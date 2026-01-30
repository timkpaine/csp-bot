"""Status command for csp-bot.

Displays system and bot status information.
"""

from datetime import datetime
from getpass import getuser
from logging import getLogger
from socket import gethostname
from threading import active_count
from typing import TYPE_CHECKING, List, Optional, Type

import psutil
from chatom import Message

from csp_bot.structs import BotCommand

from .base import BaseCommand, BaseCommandModel, ReplyCommand

if TYPE_CHECKING:
    from csp_bot import Bot

log = getLogger(__name__)

_HOSTNAME = gethostname()
_USER = getuser()


class StatusCommand(ReplyCommand):
    """Display bot and system status."""

    _adapters: List[str] = []

    def command(self) -> str:
        return "status"

    def name(self) -> str:
        return "Status"

    def help(self) -> str:
        return "Display system status. Syntax: /status [/channel <channel>]"

    def preexecute(self, command: BotCommand, bot_instance: "Bot") -> BotCommand:
        self._adapters = list(bot_instance._adapters.keys())
        return command

    def execute(self, command: BotCommand) -> Optional[Message]:
        log.info("Status command")

        # Build status information
        lines = []

        lines.append(f"**Now**: {datetime.utcnow()}")
        lines.append(f"**Backends**: {', '.join(self._adapters)}")
        lines.append(f"**CPU**: {psutil.cpu_percent()}%")
        lines.append(f"**Memory**: {psutil.virtual_memory().percent}%")
        lines.append(f"**Memory Available**: {round(psutil.virtual_memory().available * 100 / psutil.virtual_memory().total, 2)}%")
        lines.append(f"**Host**: {_HOSTNAME}")
        lines.append(f"**User**: {_USER}")

        current_process = psutil.Process()
        lines.append(f"**PID**: {current_process.pid}")
        lines.append(f"**Active Threads**: {active_count()}")

        content = "\n".join(lines)

        return Message(
            content=content,
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class StatusCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = StatusCommand
