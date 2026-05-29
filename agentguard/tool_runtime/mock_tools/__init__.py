"""Mock tool implementations."""

from agentguard.tool_runtime.mock_tools.browser import search_web
from agentguard.tool_runtime.mock_tools.calendar import (
    create_calendar_event,
    list_calendar_events,
)
from agentguard.tool_runtime.mock_tools.crm import (
    create_ticket,
    get_customer_profile,
    update_customer,
)
from agentguard.tool_runtime.mock_tools.email import send_email
from agentguard.tool_runtime.mock_tools.payments import issue_refund
from agentguard.tool_runtime.mock_tools.permissions import check_user_permissions
from agentguard.tool_runtime.mock_tools.policy_search import search_policy_docs

__all__ = [
    "check_user_permissions",
    "create_calendar_event",
    "create_ticket",
    "get_customer_profile",
    "issue_refund",
    "list_calendar_events",
    "search_policy_docs",
    "search_web",
    "send_email",
    "update_customer",
]
