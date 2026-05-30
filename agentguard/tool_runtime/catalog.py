"""MockSpec / MockMatcher / MockCatalog (BLUEPRINT-7 section 4.4.2).

A ``MockCatalog`` is a per-scope registration of:

* **static** :class:`MockSpec` entries (declared in YAML, return canned data).
* **dynamic** Python callables registered via the ``agentguard.mock_tools``
  entry-point group or the scenario-level ``mocks_module:`` reference.

Each tool call dispatched by the mock server picks the first matching entry,
preferring scenario-scope dynamic > scenario-scope static > global static.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class MockMatcher(BaseModel):
    """A ``when:`` predicate. Empty matcher matches every call.

    Each key is a dotted-path into the call kwargs, and each value is a
    ``{operator: operand}`` mapping. Supported operators: ``eq``, ``ne``,
    ``lt``, ``lte``, ``gt``, ``gte``, ``in``, ``nin``, ``contains``, ``regex``.
    Example::

        when:
          args.amount: { lte: 100 }
          args.customer.plan: { in: ["pro", "enterprise"] }
    """

    args: dict[str, dict[str, Any]] = Field(default_factory=dict)


class MockSpec(BaseModel):
    """A static mock declaration."""

    name: str
    when: MockMatcher | None = None
    status: int = 200
    response: Any = None
    delay_ms: int = 0
    raises: str | None = None  # e.g. "TimeoutError"


class MockCatalog(BaseModel):
    """Per-scope set of static specs and/or Python callables."""

    static: list[MockSpec] = Field(default_factory=list)
    dynamic: dict[str, Callable[..., Any]] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def lookup(
        self, name: str, args: dict[str, Any]
    ) -> MockSpec | Callable[..., Any] | None:
        if name in self.dynamic:
            return self.dynamic[name]
        for spec in self.static:
            if spec.name != name:
                continue
            if spec.when is None or _matches(spec.when, args):
                return spec
        return None


# ---------------------------------------------------------------------------
# Predicate engine
# ---------------------------------------------------------------------------


def _resolve_path(args: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path against ``args`` (and the synthetic ``args.`` prefix)."""
    parts = path.split(".")
    if parts and parts[0] == "args":
        parts = parts[1:]
    cursor: Any = args
    for part in parts:
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return _Missing
    return cursor


class _MissingType:
    def __repr__(self) -> str:
        return "<missing>"


_Missing = _MissingType()


_OPERATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
    "nin": lambda a, b: a not in b,
    "contains": lambda a, b: b in a,
    "regex": lambda a, b: bool(re.search(b, str(a))),
}


def _matches(matcher: MockMatcher, args: dict[str, Any]) -> bool:
    for path, operators in matcher.args.items():
        actual = _resolve_path(args, path)
        for op_name, expected in operators.items():
            op = _OPERATORS.get(op_name)
            if op is None:
                return False
            if actual is _Missing:
                return False
            try:
                if not op(actual, expected):
                    return False
            except (TypeError, ValueError):
                return False
    return True


# ---------------------------------------------------------------------------
# Execution helpers used by the server
# ---------------------------------------------------------------------------


async def execute(spec_or_callable: MockSpec | Callable, args: dict[str, Any]) -> Any:
    """Resolve a matched lookup result to a JSON-able payload."""
    if isinstance(spec_or_callable, MockSpec):
        if spec_or_callable.delay_ms:
            await asyncio.sleep(spec_or_callable.delay_ms / 1000.0)
        if spec_or_callable.raises:
            raise RuntimeError(f"mock-raised:{spec_or_callable.raises}")
        return spec_or_callable.response

    fn = spec_or_callable
    sig = inspect.signature(fn)
    kwargs = {k: v for k, v in args.items() if k in sig.parameters}
    if asyncio.iscoroutinefunction(fn):
        return await fn(**kwargs)
    return await asyncio.to_thread(fn, **kwargs)
