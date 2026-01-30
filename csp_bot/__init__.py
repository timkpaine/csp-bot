"""CSP Bot - Multi-platform chat bot using chatom.

This package provides a CSP-based bot framework that leverages
chatom for unified cross-platform chat support.

Key features:
- Unified Message, User, Channel models via chatom
- Cross-platform mention generation
- Backend-specific message formatting
- Entity recognition and parsing
- Support for Slack, Symphony, and Discord
"""

__version__ = "2.0.0"

# Re-export chatom types for convenience
from chatom import Channel, Message, User

from .bot import Bot
from .bot_config import BotConfig, DiscordConfig, SlackConfig, SymphonyConfig
from .commands import (
    BaseCommand,
    BaseCommandModel,
    EchoCommand,
    HelpCommand,
    NoResponseCommand,
    ReplyCommand,
    ReplyToAllCommand,
    ReplyToAuthorCommand,
    ReplyToOtherCommand,
    ScheduleCommand,
    StatusCommand,
    mention_user,
)
from .gateway import CspBotGateway, Gateway, GatewayChannels, GatewayModule, GatewaySettings
from .structs import Backend, BotCommand, BotMessage, CommandVariant
from .utils import format_message, get_backend_format, is_valid_url, mention_users

# Alias for backwards compatibility with tests
Channels = GatewayChannels

__all__ = (
    # Version
    "__version__",
    # Chatom re-exports
    "Channel",
    "Message",
    "User",
    # Bot
    "Bot",
    # Config
    "BotConfig",
    "DiscordConfig",
    "SlackConfig",
    "SymphonyConfig",
    # Commands
    "BaseCommand",
    "BaseCommandModel",
    "EchoCommand",
    "HelpCommand",
    "NoResponseCommand",
    "ReplyCommand",
    "ReplyToAllCommand",
    "ReplyToAuthorCommand",
    "ReplyToOtherCommand",
    "ScheduleCommand",
    "StatusCommand",
    # Gateway
    "Channels",
    "CspBotGateway",
    "Gateway",
    "GatewayChannels",
    "GatewayModule",
    "GatewaySettings",
    # Structs
    "Backend",
    "BotCommand",
    "BotMessage",
    "CommandVariant",
    # Utils
    "format_message",
    "get_backend_format",
    "is_valid_url",
    "mention_user",
    "mention_users",
)
