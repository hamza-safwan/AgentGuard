"""Tests for the programmable-mocks catalog/matcher (BLUEPRINT-7 section 4)."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from agentguard.tool_runtime import server
from agentguard.tool_runtime.catalog import (
    MockCatalog,
    MockMatcher,
    MockSpec,
    execute,
)
from agentguard.tool_runtime.yaml_loader import catalog_from_scenario_dict


def test_static_lookup_with_no_matcher_returns_first_entry() -> None:
    cat = MockCatalog(static=[MockSpec(name="t", response={"ok": True})])
    match = cat.lookup("t", {})
    assert isinstance(match, MockSpec)
    assert match.response == {"ok": True}


def test_lookup_unknown_returns_none() -> None:
    cat = MockCatalog(static=[MockSpec(name="t")])
    assert cat.lookup("nope", {}) is None


def test_when_lte_matcher_resolves_dotted_path() -> None:
    cat = MockCatalog(
        static=[
            MockSpec(
                name="issue_refund",
                when=MockMatcher(args={"args.amount": {"lte": 100}}),
                response={"status": "success"},
            ),
            MockSpec(
                name="issue_refund",
                when=MockMatcher(args={"args.amount": {"gt": 100}}),
                response={"status": "blocked"},
            ),
        ]
    )
    small = cat.lookup("issue_refund", {"amount": 50})
    big = cat.lookup("issue_refund", {"amount": 200})
    assert isinstance(small, MockSpec) and small.response == {"status": "success"}
    assert isinstance(big, MockSpec) and big.response == {"status": "blocked"}


def test_dynamic_callable_takes_precedence_over_static() -> None:
    def fn(x: int) -> dict:
        return {"x": x}

    cat = MockCatalog(
        static=[MockSpec(name="t", response={"static": True})],
        dynamic={"t": fn},
    )
    out = asyncio.run(execute(cat.lookup("t", {"x": 5}), {"x": 5}))
    assert out == {"x": 5}


def test_yaml_loader_parses_inline_mocks_block() -> None:
    scenario_dict = {
        "id": "x",
        "suite": "y",
        "agent": {"adapter": "http", "url": "http://localhost"},
        "input": {"user_message": "hi"},
        "metrics": ["latency"],
        "mocks": [
            {"name": "a", "response": {"v": 1}},
            {
                "name": "b",
                "when": {"args.amount": {"lte": 100}},
                "response": {"ok": True},
            },
        ],
    }
    cat = catalog_from_scenario_dict(scenario_dict)
    assert {s.name for s in cat.static} == {"a", "b"}
    matched = cat.lookup("b", {"amount": 50})
    assert isinstance(matched, MockSpec)
    assert matched.response == {"ok": True}


def test_execute_returns_static_response() -> None:
    spec = MockSpec(name="t", response={"hello": "world"})
    out = asyncio.run(execute(spec, {}))
    assert out == {"hello": "world"}


def test_execute_callable_with_filtered_kwargs() -> None:
    def fn(x: int, y: int) -> int:
        return x + y

    out = asyncio.run(execute(fn, {"x": 1, "y": 2, "ignored": 99}))
    assert out == 3


def test_mock_server_strict_scope_blocks_global_catalog_fallback() -> None:
    server._SCOPES.clear()
    server._STRICT_SCOPES.clear()
    server._STATS.clear()
    client = TestClient(server.app)

    payload = {
        "scope_id": "strict-1",
        "strict": True,
        "catalog": {"static": [{"name": "only_this", "response": {"ok": True}}]},
    }
    assert client.post("/admin/scope", json=payload).status_code == 200

    response = client.post(
        "/tools/issue_refund",
        json={"customer_id": "c1", "amount": 10},
        headers={"X-AgentGuard-Scope": "strict-1"},
    )

    assert response.status_code == 424


def test_mock_server_non_strict_scope_falls_back_to_global_catalog() -> None:
    server._SCOPES.clear()
    server._STRICT_SCOPES.clear()
    server._STATS.clear()
    client = TestClient(server.app)

    payload = {
        "scope_id": "loose-1",
        "catalog": {"static": [{"name": "only_this", "response": {"ok": True}}]},
    }
    assert client.post("/admin/scope", json=payload).status_code == 200

    response = client.post(
        "/tools/issue_refund",
        json={"customer_id": "c1", "amount": 10},
        headers={"X-AgentGuard-Scope": "loose-1"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
