"""Agent framework adapters."""

from agentguard.adapters.base import BaseAgentAdapter
from agentguard.adapters.http import HTTPAdapter

__all__ = ["BaseAgentAdapter", "HTTPAdapter"]
