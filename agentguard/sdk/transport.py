"""Observability transport (BLUEPRINT-7 section 12.8).

Background queue + batched, gzipped ``POST /api/v2/traces/ingest`` shipper.
The transport is **off by default**; calling :func:`configure` (or its alias
``agentguard.observability.configure``) installs the global instance and
``trace()`` blocks start auto-shipping their captured traces on close.

Bounded queue, deterministic sampler keyed on ``trace_id`` so retries don't
double-count, exponential backoff, fail-open on persistent network errors so
production agents are never blocked by AgentGuard ingest issues.
"""

from __future__ import annotations

import contextlib
import gzip
import json
import queue
import threading
import time
from dataclasses import dataclass, field

import httpx

from agentguard.schemas.trace import AgentTrace

WIRE_SCHEMA_URI = "https://schemas.agentguard.dev/v1/trace.json"


@dataclass
class IngestConfig:
    endpoint: str
    token: str
    batch_size: int = 20
    flush_interval_seconds: float = 2.0
    sample_rate: float = 1.0
    max_queue: int = 10_000
    always_sample_errors: bool = True
    on_error: str = "warn"  # "warn" | "raise" | "silent"
    extra_headers: dict[str, str] = field(default_factory=dict)


class _IngestQueue:
    """Background-threaded sender. One per configured endpoint."""

    def __init__(self, config: IngestConfig) -> None:
        self._cfg = config
        self._q: queue.Queue[AgentTrace] = queue.Queue(maxsize=config.max_queue)
        self._stop = threading.Event()
        self._dropped = 0
        self._sent = 0
        self._failed = 0
        self._thread = threading.Thread(
            target=self._loop,
            name="agentguard-ingest",
            daemon=True,
        )
        self._thread.start()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def submit(self, trace: AgentTrace) -> None:
        if not self._should_keep(trace):
            return
        try:
            self._q.put_nowait(trace)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                self._q.get_nowait()
            with contextlib.suppress(queue.Full):
                self._q.put_nowait(trace)
            self._dropped += 1

    def shutdown(self, timeout: float | None = 5.0) -> None:
        self._stop.set()
        self._thread.join(timeout=timeout)

    def stats(self) -> dict[str, int]:
        return {
            "queued": self._q.qsize(),
            "sent": self._sent,
            "failed": self._failed,
            "dropped": self._dropped,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _should_keep(self, trace: AgentTrace) -> bool:
        if self._cfg.always_sample_errors and any(
            s.type == "error" for s in trace.steps
        ):
            return True
        # Deterministic head sampler keyed on trace_id so retries are stable.
        h = abs(hash(trace.trace_id)) & 0xFFFF
        return (h / 0xFFFF) < self._cfg.sample_rate

    def _loop(self) -> None:
        batch: list[AgentTrace] = []
        last_flush = time.time()
        while not self._stop.is_set():
            try:
                trace = self._q.get(timeout=0.1)
                batch.append(trace)
            except queue.Empty:
                pass
            should_flush = batch and (
                len(batch) >= self._cfg.batch_size
                or (time.time() - last_flush) > self._cfg.flush_interval_seconds
            )
            if should_flush:
                self._flush(batch)
                batch = []
                last_flush = time.time()
        if batch:
            self._flush(batch)

    def _flush(self, batch: list[AgentTrace]) -> None:
        body = json.dumps(
            {
                "$schema": WIRE_SCHEMA_URI,
                "traces": [t.model_dump(mode="json") for t in batch],
            },
            default=str,
        ).encode("utf-8")
        gzipped = gzip.compress(body)
        headers = {
            "Authorization": f"Bearer {self._cfg.token}",
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            **self._cfg.extra_headers,
        }
        for attempt in range(3):
            try:
                response = httpx.post(
                    self._cfg.endpoint,
                    headers=headers,
                    content=gzipped,
                    timeout=5.0,
                )
                if response.status_code < 400:
                    self._sent += len(batch)
                    return
                # 4xx (except 429) won't recover by retry; bail early.
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5 * (2**attempt))
        self._failed += len(batch)
        if self._cfg.on_error == "raise":
            raise RuntimeError(
                f"AgentGuard ingest failed for {len(batch)} traces after retries."
            )
        if self._cfg.on_error == "warn":
            print(
                f"AgentGuard ingest dropped {len(batch)} traces after retries.",
                flush=True,
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


_ACTIVE: _IngestQueue | None = None


def configure(
    endpoint: str,
    token: str,
    *,
    batch_size: int = 20,
    flush_interval_seconds: float = 2.0,
    sample_rate: float = 1.0,
    max_queue: int = 10_000,
    always_sample_errors: bool = True,
    on_error: str = "warn",
    extra_headers: dict[str, str] | None = None,
) -> None:
    """Install (or replace) the global observability transport."""
    global _ACTIVE
    cfg = IngestConfig(
        endpoint=endpoint,
        token=token,
        batch_size=batch_size,
        flush_interval_seconds=flush_interval_seconds,
        sample_rate=sample_rate,
        max_queue=max_queue,
        always_sample_errors=always_sample_errors,
        on_error=on_error,
        extra_headers=extra_headers or {},
    )
    if _ACTIVE is not None:
        _ACTIVE.shutdown(timeout=1.0)
    _ACTIVE = _IngestQueue(cfg)


def ship_trace(trace: AgentTrace) -> None:
    """Queue ``trace`` for ingest if the transport has been configured."""
    if _ACTIVE is not None:
        _ACTIVE.submit(trace)


def shutdown() -> None:
    """Stop the active transport (used by tests; rarely needed in user code)."""
    global _ACTIVE
    if _ACTIVE is not None:
        _ACTIVE.shutdown(timeout=2.0)
        _ACTIVE = None


def stats() -> dict[str, int] | None:
    return _ACTIVE.stats() if _ACTIVE is not None else None


def is_configured() -> bool:
    return _ACTIVE is not None


# Reset hook for tests (NOT public API).
def _reset_for_tests() -> None:
    shutdown()
