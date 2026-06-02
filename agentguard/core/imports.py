"""Dynamic import helpers for adapters that need to load user code."""

from __future__ import annotations

import importlib
from typing import Any


def import_object(module_path: str, object_name: str) -> Any:
    """Dynamically import a Python object from a module.

    Example:
        import_object("examples.customer_support.agent", "graph")
    """
    module = importlib.import_module(module_path)
    return getattr(module, object_name)
