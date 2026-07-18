"""Bot commands for csp-bot.

Commands can leverage chatom's cross-platform features for
mentions, formatting, and entity recognition.

Two command APIs are available:

1. ``@command`` decorator for stateless function-based commands
2. ``Command`` BaseModel subclass for stateful class-based commands

The legacy ``BaseCommand`` hierarchy is still supported via
``LegacyCommandAdapter``.
"""

from csp_bot.utils import mention_user

from .base import (
    BaseCommand,
    BaseCommandModel,
    NoResponseCommand,
    ReplyCommand,
    ReplyToAllCommand,
    ReplyToAuthorCommand,
    ReplyToOtherCommand,
)
from .context import BotInfo, CommandContext
from .echo import EchoCommand, EchoCommandModel
from .executor import execute_command_func
from .framework import Command, CommandEntry, CommandModel, clear_registry, command, get_registered_commands
from .help import HelpCommand, HelpCommandModel
from .legacy import LegacyCommandAdapter
from .schedule import ScheduleCommand, ScheduleCommandModel
from .status import StatusCommand, StatusCommandModel

try:
    from .agent import AgentCommand
except ImportError:
    pass

__all__ = (
    # New framework
    "Command",
    "CommandContext",
    "CommandEntry",
    "CommandModel",
    "BotInfo",
    "LegacyCommandAdapter",
    "command",
    "clear_registry",
    "get_registered_commands",
    "execute_command_func",
    # Legacy base classes
    "AgentCommand",
    "BaseCommand",
    "BaseCommandModel",
    "NoResponseCommand",
    "ReplyCommand",
    "ReplyToAllCommand",
    "ReplyToAuthorCommand",
    "ReplyToOtherCommand",
    # Built-in commands
    "EchoCommand",
    "EchoCommandModel",
    "HelpCommand",
    "HelpCommandModel",
    "ScheduleCommand",
    "ScheduleCommandModel",
    "StatusCommand",
    "StatusCommandModel",
    # Utilities
    "mention_user",
)
