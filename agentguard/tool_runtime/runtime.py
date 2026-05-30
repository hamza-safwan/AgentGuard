"""Scenario-scoped lifecycle helpers for the programmable mock server.

Used by ``agentguard.core.runner`` and the pytest plugin to:

1. Build a :class:`MockCatalog` from the scenario's ``mocks:`` / ``mocks_module:``.
2. Register it with a running mock server under a unique scope id.
3. Tear it down on scenario exit.

If no mock server is running, registration is silently skipped (the scenario
will fall through to whatever the agent reaches over its own HTTP).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager, suppress

import httpx

from agentguard.tool_runtime.catalog import MockCatalog
from agentguard.tool_runtime.yaml_loader import catalog_from_scenario_dict

SCOPE_HEADER = "X-AgentGuard-Scope"


def mock_server_base_url(port: int | None = None) -> str:
    if port is not None:
        return f"http://localhost:{port}"
    return (
        os.getenv("AGENTGUARD_MOCK_SERVER_URL")
        or os.getenv("AGENTGUARD_MOCK_BASE_URL")
        or "http://localhost:8100"
    )


def _server_reachable(url: str) -> bool:
    try:
        r = httpx.get(url + "/health", timeout=0.5)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def register_scope(
    catalog: MockCatalog,
    *,
    port: int | None = None,
    strict: bool = False,
) -> str | None:
    """Register a catalog with the running mock server. Returns the scope id, or None."""
    if not catalog.static and not catalog.dynamic:
        return None
    base = mock_server_base_url(port)
    if not _server_reachable(base):
        return None
    scope_id = uuid.uuid4().hex
    payload = {
        "scope_id": scope_id,
        "strict": strict,
        "catalog": {
            "static": [s.model_dump() for s in catalog.static],
            # Dynamic Python callables can't be serialised; they only matter when
            # the server itself loaded the same module via the entry-point group.
            "dynamic_names": list(catalog.dynamic.keys()),
        },
    }
    try:
        r = httpx.post(base + "/admin/scope", json=payload, timeout=2.0)
        if r.status_code >= 400:
            return None
    except httpx.HTTPError:
        return None
    return scope_id


def teardown_scope(scope_id: str | None, *, port: int | None = None) -> None:
    if not scope_id:
        return
    base = mock_server_base_url(port)
    with suppress(httpx.HTTPError):
        httpx.post(base + f"/admin/scope/{scope_id}/teardown", timeout=2.0)


@contextmanager
def scenario_scope(
    scenario_dict: dict,
    *,
    mock_port: int | None = None,
    strict: bool = False,
) -> Iterator[str | None]:
    """Build a catalog from a scenario dict, register it, yield the scope id, tear down."""
    catalog = catalog_from_scenario_dict(scenario_dict)
    scope_id = register_scope(catalog, port=mock_port, strict=strict)
    try:
        yield scope_id
    finally:
        teardown_scope(scope_id, port=mock_port)
