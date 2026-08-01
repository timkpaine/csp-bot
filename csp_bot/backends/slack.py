"""Slack backend integration using chatom.

This module provides Slack-specific types and adapters through chatom.
"""

__all__ = (
    "SlackAdapter",
    "SlackConfig",
    "SlackMessage",
    "SlackPresenceStatus",
    "SlackUser",
)

try:
    from chatom.slack import (
        SlackConfig,
        SlackMessage,
        SlackPresenceStatus,
        SlackUser,
    )
    from csp_adapter_slack.v1 import SlackAdapter
except ImportError:
    from chatom import Message as ChatomMessage, User as ChatomUser
    from pydantic import BaseModel

    class SlackConfig(BaseModel):
        """Placeholder when chatom.slack is not available."""

    SlackAdapter = None
    SlackMessage = ChatomMessage
    SlackUser = ChatomUser
    SlackPresenceStatus = None
