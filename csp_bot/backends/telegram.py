"""Telegram backend integration using chatom.

This module provides Telegram-specific types and adapters through chatom.
"""

__all__ = (
    "TelegramConfig",
    "TelegramAdapter",
    "TelegramMessage",
    "TelegramUser",
)

try:
    from chatom.telegram import (
        TelegramConfig,
        TelegramMessage,
        TelegramUser,
    )
    from csp_adapter_telegram import TelegramAdapter
except ImportError:
    from chatom import Message as ChatomMessage, User as ChatomUser
    from pydantic import BaseModel

    class TelegramConfig(BaseModel):
        """Placeholder when chatom.telegram is not available."""

        pass

    TelegramAdapter = None
    TelegramMessage = ChatomMessage
    TelegramUser = ChatomUser
