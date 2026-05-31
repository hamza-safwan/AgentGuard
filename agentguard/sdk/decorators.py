"""SDK decorators (BLUEPRINT-7 section 6.5.1).

Decorating a function records one ``TraceStep`` per call into the active
trace, if any.  The decorators support both sync and async callables and
accept either bare-decorator (``@tool``) or factory (``@tool(name="x")``)
syntax.

Default capture: arguments and return values are JSON-serialized with a
size cap (``AGENTGUARD_MAX_CAPTURE_BYTES``, default 4096). Sensitive
field names registered via ``scrub()`` are replaced with ``"***"``.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import os
import time
from collections.abc import Callable, Iterable
from typing import Any

from agentguard.schemas.trace import TraceStep, TraceStepType
from agentguard.sdk.context import record_step

DEFAULT_MAX_CAPTURE_BYTES = 4096

_scrub_keys: set[str] = {
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "authorization",
    "openai_api_key",
    "anthropic_api_key",
}


def scrub(*keys: str) -> None:
    """Register additional argument / output keys to redact when captured.

    Matches against dict keys at any depth (case-insensitive). Already-included
    keys: password, secret, api_key, token, authorization, openai_api_key,
    anthropic_api_key.
    """
    for k in keys:
        _scrub_keys.add(k.lower())


def _max_bytes() -> int:
    try:
        return int(os.getenv("AGENTGUARD_MAX_CAPTURE_BYTES", str(DEFAULT_MAX_CAPTURE_BYTES)))
    except ValueError:
        return DEFAULT_MAX_CAPTURE_BYTES


def _redact(value: Any) -> tuple[Any, list[str]]:
    """Return (redacted_value, list_of_scrubbed_field_paths)."""
    redactions: list[str] = []

    def walk(node: Any, path: str) -> Any:
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for k, v in node.items():
                key_lower = str(k).lower()
                child_path = f"{path}.{k}" if path else str(k)
                if key_lower in _scrub_keys:
                    out[k] = "***"
                    redactions.append(child_path)
                else:
                    out[k] = walk(v, child_path)
            return out
        if isinstance(node, (list, tuple)):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(node)]
        return node

    return walk(value, ""), redactions


def _jsonable(value: Any) -> Any:
    """Convert value to a JSON-serializable form, truncating if too large."""
    try:
        text = json.dumps(value, default=str)
    except (TypeError, ValueError):
        text = repr(value)
    cap = _max_bytes()
    if len(text) > cap:
        text = text[:cap] + f"...<truncated {len(text) - cap} bytes>"
        return text
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def _capture_args(fn: Callable, args: tuple, kwargs: dict) -> tuple[dict, list[str]]:
    """Bind args/kwargs to parameter names; return (captured_dict, redactions)."""
    try:
        sig = inspect.signature(fn)
        bound = sig.bind_partial(*args, **kwargs)
        captured: dict[str, Any] = dict(bound.arguments)
    except (TypeError, ValueError):
        captured = {"args": list(args), "kwargs": kwargs}
    redacted, redactions = _redact(captured)
    return _jsonable(redacted), redactions


def _build_step(
    *,
    kind: TraceStepType,
    name: str,
    captured_input: Any,
    output: Any,
    started_at: float,
    capture_input: bool,
    capture_output: bool,
    metadata: dict[str, Any] | None,
    input_redactions: list[str],
) -> TraceStep:
    output_value: Any = None
    output_redactions: list[str] = []
    if capture_output:
        redacted_output, output_redactions = _redact(output)
        output_value = _jsonable(redacted_output)
    return TraceStep(
        type=kind,
        name=name,
        input=captured_input if capture_input else None,
        output=output_value,
        metadata=metadata or {},
        latency_ms=int((time.time() - started_at) * 1000),
        source="sdk",
        redactions=input_redactions + output_redactions,
    )


def _wrap(
    fn: Callable,
    *,
    kind: TraceStepType,
    label: str,
    capture_input: bool,
    capture_output: bool,
    metadata: dict[str, Any] | None,
):
    is_coro = asyncio.iscoroutinefunction(fn)

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        captured, redactions = (
            _capture_args(fn, args, kwargs) if capture_input else (None, [])
        )
        started = time.time()
        try:
            output = fn(*args, **kwargs)
        except Exception as exc:
            record_step(
                TraceStep(
                    type="error",
                    name=label,
                    input=captured,
                    output={"error_type": type(exc).__name__, "message": str(exc)},
                    metadata=metadata or {},
                    latency_ms=int((time.time() - started) * 1000),
                    source="sdk",
                    redactions=redactions,
                )
            )
            raise
        record_step(
            _build_step(
                kind=kind,
                name=label,
                captured_input=captured,
                output=output,
                started_at=started,
                capture_input=capture_input,
                capture_output=capture_output,
                metadata=metadata,
                input_redactions=redactions,
            )
        )
        return output

    @functools.wraps(fn)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        captured, redactions = (
            _capture_args(fn, args, kwargs) if capture_input else (None, [])
        )
        started = time.time()
        try:
            output = await fn(*args, **kwargs)
        except Exception as exc:
            record_step(
                TraceStep(
                    type="error",
                    name=label,
                    input=captured,
                    output={"error_type": type(exc).__name__, "message": str(exc)},
                    metadata=metadata or {},
                    latency_ms=int((time.time() - started) * 1000),
                    source="sdk",
                    redactions=redactions,
                )
            )
            raise
        record_step(
            _build_step(
                kind=kind,
                name=label,
                captured_input=captured,
                output=output,
                started_at=started,
                capture_input=capture_input,
                capture_output=capture_output,
                metadata=metadata,
                input_redactions=redactions,
            )
        )
        return output

    return async_wrapper if is_coro else sync_wrapper


_RESERVED = {"name", "capture_input", "capture_output", "metadata"}


def _factory(default_kind: TraceStepType):
    def deco(
        *dargs: Any,
        name: str | None = None,
        capture_input: bool = True,
        capture_output: bool = True,
        metadata: dict[str, Any] | None = None,
        **extra: Any,
    ):
        # Any kwarg that is not one of the reserved decorator-control kwargs is
        # folded into the step metadata. This lets users write
        # ``@llm_call(model="gpt-4.1-mini", temperature=0)`` ergonomically.
        merged_metadata = {**(metadata or {}), **extra}

        # Bare decorator usage: @tool def foo(): ...
        if dargs and callable(dargs[0]) and not isinstance(dargs[0], type):
            fn = dargs[0]
            return _wrap(
                fn,
                kind=default_kind,
                label=name or fn.__name__,
                capture_input=capture_input,
                capture_output=capture_output,
                metadata=merged_metadata,
            )

        # Parametrized usage: @tool(name="x") def foo(): ...
        def wrap(fn: Callable) -> Callable:
            return _wrap(
                fn,
                kind=default_kind,
                label=name or fn.__name__,
                capture_input=capture_input,
                capture_output=capture_output,
                metadata=merged_metadata,
            )

        return wrap

    return deco


tool = _factory("tool_call")
llm_call = _factory("llm_call")
retrieval = _factory("retrieval")
guardrail = _factory("guardrail")
traceable = _factory("tool_call")  # generic alias for any user-defined step


__all__: Iterable[str] = [
    "tool",
    "llm_call",
    "retrieval",
    "guardrail",
    "traceable",
    "scrub",
]
