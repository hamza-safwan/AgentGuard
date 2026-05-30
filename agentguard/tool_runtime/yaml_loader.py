"""Build :class:`MockCatalog` instances from scenario YAML mocks blocks."""

from __future__ import annotations

from typing import Any

from agentguard.core.imports import import_object
from agentguard.tool_runtime.catalog import MockCatalog, MockMatcher, MockSpec


def catalog_from_scenario_dict(data: dict[str, Any]) -> MockCatalog:
    """Build a :class:`MockCatalog` from the ``mocks:`` and ``mocks_module:`` keys.

    Returns an empty catalog if neither key is present.
    """
    static: list[MockSpec] = []
    dynamic: dict[str, Any] = {}

    for entry in data.get("mocks") or []:
        when_dict = entry.get("when")
        when_obj: MockMatcher | None = None
        if when_dict:
            # Accept either `{args.amount: {lte: 100}}` or `{args: {amount: {lte: 100}}}`.
            if any(k.startswith("args.") for k in when_dict):
                args = dict(when_dict.items())
            elif "args" in when_dict and isinstance(when_dict["args"], dict):
                args = {f"args.{k}": v for k, v in when_dict["args"].items()}
            else:
                args = when_dict
            when_obj = MockMatcher(args=args)
        static.append(
            MockSpec(
                name=entry["name"],
                when=when_obj,
                status=entry.get("status", 200),
                response=entry.get("response"),
                delay_ms=entry.get("delay_ms", 0),
                raises=entry.get("raises"),
            )
        )

    module_ref = data.get("mocks_module")
    if module_ref:
        module_path, _, attr = module_ref.partition(":")
        if not attr:
            raise ValueError(
                f"mocks_module must be 'module.path:ATTRIBUTE_NAME', got {module_ref!r}"
            )
        loaded = import_object(module_path, attr)
        if isinstance(loaded, MockCatalog):
            static.extend(loaded.static)
            dynamic.update(loaded.dynamic)
        elif isinstance(loaded, dict):
            dynamic.update(loaded)
        elif callable(loaded):
            dynamic[attr] = loaded
        else:
            raise TypeError(
                f"mocks_module symbol must be MockCatalog | dict[str, Callable] | Callable, "
                f"got {type(loaded).__name__}"
            )

    return MockCatalog(static=static, dynamic=dynamic)
