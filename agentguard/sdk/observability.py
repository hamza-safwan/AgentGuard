"""Public observability surface (BLUEPRINT-7 section 12.3.1).

``agentguard.observability.configure(endpoint, token, ...)`` is the user-facing
opt-in. Once configured, every ``with agentguard.trace():`` block ships its
trace asynchronously to the configured endpoint subject to sampling.
"""

from __future__ import annotations

from agentguard.sdk.transport import (
    configure,
    is_configured,
    ship_trace,
    shutdown,
    stats,
)

__all__ = [
    "configure",
    "is_configured",
    "ship_trace",
    "shutdown",
    "stats",
]
