"""Programmable mock tool server (BLUEPRINT-7 section 4).

Backwards-compatible upgrade of the v0.1 server:

* The legacy global catalog (CRM, email, payments, calendar, browser,
  policy_search, permissions) is preserved as the fallback.
* Scenarios can register per-scope catalogs via ``POST /admin/scope`` and tear
  them down via ``POST /admin/scope/<id>/teardown``. Lookup is keyed on the
  ``X-AgentGuard-Scope`` header that AgentGuard adapters set automatically.
* Strict scopes return 424 for unregistered tool calls instead of falling
  through to the global catalog.
* Plugin catalogs registered via the ``agentguard.mock_tools`` entry-point
  group are merged into the global catalog at server start.

Run with::

    python -m agentguard.tool_runtime.server   # binds 0.0.0.0:8100
"""

from __future__ import annotations

import inspect
import logging
import traceback
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from agentguard.core.registry import _discovered_mock_catalogs
from agentguard.tool_runtime import mock_tools
from agentguard.tool_runtime.catalog import MockCatalog, MockSpec, execute

_log = logging.getLogger(__name__)
app = FastAPI(title="agentguard-mock-tools", version="2.0.0")


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------

_BUILTIN_CALLABLES: dict[str, Any] = {
    name: getattr(mock_tools, name)
    for name in mock_tools.__all__
    if callable(getattr(mock_tools, name))
}

_GLOBAL_CATALOG = MockCatalog(static=[], dynamic=dict(_BUILTIN_CALLABLES))

# Merge plugin-registered catalogs into the global one at import time.
for _plugin_name, _plugin in _discovered_mock_catalogs().items():
    if isinstance(_plugin, MockCatalog):
        _GLOBAL_CATALOG.static.extend(_plugin.static)
        _GLOBAL_CATALOG.dynamic.update(_plugin.dynamic)
    elif isinstance(_plugin, dict):
        _GLOBAL_CATALOG.dynamic.update(_plugin)
    elif callable(_plugin):
        _GLOBAL_CATALOG.dynamic[_plugin_name] = _plugin

# Scope id -> catalog. Cleaned up on /admin/scope/<id>/teardown.
_SCOPES: dict[str, MockCatalog] = {}
_STRICT_SCOPES: set[str] = set()

# Per-scope call statistics - exposed on /admin/stats.
_STATS: dict[str, dict[str, int]] = {}


def _stat(scope_id: str, key: str) -> None:
    _STATS.setdefault(scope_id, {"matched": 0, "unmatched": 0, "errors": 0})[key] += 1


# ---------------------------------------------------------------------------
# Scope-registration models
# ---------------------------------------------------------------------------


class _ScopePayload(BaseModel):
    scope_id: str
    strict: bool = False
    catalog: dict[str, Any]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
def index() -> dict[str, Any]:
    return {
        "name": "agentguard-mock-tools",
        "version": "2.0.0",
        "global_tools": sorted(_GLOBAL_CATALOG.dynamic.keys()),
        "active_scopes": list(_SCOPES.keys()),
        "endpoint": "POST /tools/{tool_name}",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {"name": name, "signature": str(inspect.signature(fn))}
            for name, fn in _GLOBAL_CATALOG.dynamic.items()
        ]
    }


@app.post("/admin/scope")
def register_scope(payload: _ScopePayload) -> dict[str, Any]:
    """Register a scenario-scoped catalog. Idempotent on scope_id."""
    static = [MockSpec(**s) for s in payload.catalog.get("static", [])]
    # Plugin-side dynamic callables are looked up by name from the global catalog.
    dynamic_names = payload.catalog.get("dynamic_names") or []
    dynamic = {n: _GLOBAL_CATALOG.dynamic[n] for n in dynamic_names if n in _GLOBAL_CATALOG.dynamic}
    _SCOPES[payload.scope_id] = MockCatalog(static=static, dynamic=dynamic)
    if payload.strict:
        _STRICT_SCOPES.add(payload.scope_id)
    else:
        _STRICT_SCOPES.discard(payload.scope_id)
    _STATS.setdefault(payload.scope_id, {"matched": 0, "unmatched": 0, "errors": 0})
    return {"ok": True, "scope_id": payload.scope_id}


@app.post("/admin/scope/{scope_id}/teardown")
def teardown_scope(scope_id: str) -> dict[str, Any]:
    _SCOPES.pop(scope_id, None)
    _STRICT_SCOPES.discard(scope_id)
    stats = _STATS.pop(scope_id, None)
    return {"ok": True, "stats": stats}


@app.get("/admin/stats")
def stats() -> dict[str, Any]:
    return {"scopes": _STATS}


@app.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    payload: dict[str, Any],
    scope: str | None = Header(default=None, alias="X-AgentGuard-Scope"),
) -> Any:
    is_strict = bool(scope and scope in _STRICT_SCOPES)
    catalog = _SCOPES.get(scope) if scope else None
    match = catalog.lookup(tool_name, payload) if catalog else None
    if match is None and not is_strict:
        match = _GLOBAL_CATALOG.lookup(tool_name, payload)
    if match is None:
        if scope:
            _stat(scope, "unmatched")
        status_code = 424 if is_strict else 404
        raise HTTPException(status_code=status_code, detail=f"Unknown tool: {tool_name}")

    if scope:
        _stat(scope, "matched")
    try:
        return await execute(match, payload)
    except Exception as exc:
        if scope:
            _stat(scope, "errors")
        detail = traceback.format_exc() if is_strict else f"mock-error: {exc}"
        raise HTTPException(status_code=500, detail=detail) from exc


def main() -> None:
    uvicorn.run("agentguard.tool_runtime.server:app", host="0.0.0.0", port=8100, reload=False)


if __name__ == "__main__":
    main()
