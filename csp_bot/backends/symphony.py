"""Symphony backend integration using chatom.

This module provides Symphony-specific types and adapters through chatom.
"""

__all__ = (
    "SymphonyAdapter",
    "SymphonyConfig",
    "SymphonyMessage",
    "SymphonyPresenceStatus",
    "SymphonyUser",
)

try:
    from chatom.symphony import (
        SymphonyConfig,
        SymphonyMessage,
        SymphonyPresenceStatus,
        SymphonyUser,
    )
    from csp_adapter_symphony.v1 import SymphonyAdapter
except ImportError:
    from chatom import Message as ChatomMessage, User as ChatomUser
    from pydantic import BaseModel

    class SymphonyConfig(BaseModel):
        """Placeholder when chatom.symphony is not available."""

    SymphonyAdapter = None
    SymphonyMessage = ChatomMessage
    SymphonyUser = ChatomUser
    SymphonyPresenceStatus = None
