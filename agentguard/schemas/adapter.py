"""Adapter metadata model."""

from __future__ import annotations

from pydantic import BaseModel


class AdapterMeta(BaseModel):
    name: str
    description: str
    requires_module_import: bool
    supports_streaming: bool = False
    supports_async: bool = True
