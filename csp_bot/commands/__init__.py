"""Bot commands for csp-bot.

Commands can leverage chatom's cross-platform features for
mentions, formatting, and entity recognition.
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
from .echo import EchoCommand, EchoCommandModel
from .help import HelpCommand, HelpCommandModel
from .schedule import ScheduleCommand, ScheduleCommandModel
from .status import StatusCommand, StatusCommandModel

__all__ = (
    # Base classes
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
