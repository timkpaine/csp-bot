"""Status command for csp-bot.

Displays system and bot status information using FormattedMessage.
"""

from datetime import datetime
from getpass import getuser
from logging import getLogger
from socket import gethostname
from threading import active_count
from typing import TYPE_CHECKING, List, Optional, Type

import psutil
from chatom import Message
from chatom.format import Bold, FormattedMessage, Table, Text

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

        mem = psutil.virtual_memory()
        proc = psutil.Process()

        rows = [
            {"Metric": "Now", "Value": str(datetime.utcnow())},
            {"Metric": "Backends", "Value": ", ".join(self._adapters)},
            {"Metric": "CPU", "Value": f"{psutil.cpu_percent()}%"},
            {"Metric": "Memory", "Value": f"{mem.percent}%"},
            {"Metric": "Memory Available", "Value": f"{round(mem.available * 100 / mem.total, 2)}%"},
            {"Metric": "Host", "Value": _HOSTNAME},
            {"Metric": "User", "Value": _USER},
            {"Metric": "PID", "Value": str(proc.pid)},
            {"Metric": "Active Threads", "Value": str(active_count())},
        ]

        msg = FormattedMessage(metadata={"backend": command.backend})
        msg.content.append(Bold(child=Text(content="Bot Status")))
        msg.content.append(Table.from_dict_list(rows, columns=["Metric", "Value"]))

        return Message(
            content=msg.render_for(command.backend),
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class StatusCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = StatusCommand
