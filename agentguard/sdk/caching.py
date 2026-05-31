"""Judge result cache (BLUEPRINT-7 section 6.5.4).

File-backed JSON cache under ``~/.agentguard/judge-cache/``. Optional Redis
backend selected via ``AGENTGUARD_JUDGE_CACHE=redis://...``. Cache keys are
sha256 of the prompt; values are the parsed judge response.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol


class _CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...


class _FileCache:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: Any) -> None:
        with contextlib.suppress(OSError):
            self._path(key).write_text(json.dumps(value), encoding="utf-8")


class _RedisCache:
    def __init__(self, url: str, ttl_seconds: int = 86400 * 30):
        import redis  # imported lazily

        self.client = redis.from_url(url)
        self.ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        try:
            raw = self.client.get(f"agentguard:judge:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        with contextlib.suppress(Exception):
            self.client.setex(
                f"agentguard:judge:{key}", self.ttl, json.dumps(value)
            )


class _NullCache:
    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: Any) -> None:
        return None


class _JudgeCache:
    """Lazily-initialized facade chosen by env var on first use."""

    def __init__(self) -> None:
        self._backend: _CacheBackend | None = None

    def _resolve(self) -> _CacheBackend:
        if self._backend is not None:
            return self._backend
        url = os.getenv("AGENTGUARD_JUDGE_CACHE", "")
        if url.startswith("redis://") or url.startswith("rediss://"):
            try:
                self._backend = _RedisCache(url)
                return self._backend
            except Exception:
                # Fall through to file cache if redis is misconfigured
                pass
        if url == "off":
            self._backend = _NullCache()
            return self._backend
        root = Path(os.path.expanduser("~/.agentguard/judge-cache"))
        self._backend = _FileCache(root)
        return self._backend

    @staticmethod
    def key_for(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> Any | None:
        return self._resolve().get(self.key_for(prompt))

    def set(self, prompt: str, value: Any) -> None:
        self._resolve().set(self.key_for(prompt), value)


judge_cache = _JudgeCache()
