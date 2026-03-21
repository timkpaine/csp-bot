"""Discord backend integration using chatom.

This module provides Discord-specific types and adapters through chatom.
"""

__all__ = (
    "DiscordConfig",
    "DiscordAdapter",
    "DiscordMessage",
    "DiscordUser",
)

try:
    from chatom.discord import (
        DiscordConfig,
        DiscordMessage,
        DiscordUser,
    )
    from csp_adapter_discord import DiscordAdapter
except ImportError:
    from chatom import Message as ChatomMessage, User as ChatomUser
    from pydantic import BaseModel

    class DiscordConfig(BaseModel):
        """Placeholder when chatom.discord is not available."""

        pass

    DiscordAdapter = None
    DiscordMessage = ChatomMessage
    DiscordUser = ChatomUser
