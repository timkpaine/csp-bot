from datetime import datetime
from getpass import getuser
from logging import getLogger
from socket import gethostname
from threading import active_count
from typing import TYPE_CHECKING, Optional, Type

import psutil

from csp_bot.structs import BotCommand, Message

from .base import BaseCommand, BaseCommandModel, ReplyCommand

if TYPE_CHECKING:
    from csp_bot import Bot

log = getLogger(__name__)

_HOSTNAME = gethostname()
_USER = getuser()


class StatusCommand(ReplyCommand):
    def command(self) -> str:
        return "status"

    def name(self) -> str:
        return "status"

    def help(self) -> str:
        return "System information. Syntax: /status [/channel <channel>]"

    def preexecute(self, command: BotCommand, bot_instance: "Bot") -> BotCommand:
        # TODO: pull out everything except auth keys?
        self._adapters = list(bot_instance._adapters.keys())
        return command

    def execute(self, command: BotCommand) -> Optional[Message]:
        log.info(f"Status command: {command}")

        message = ""

        # Time information
        message += f"Now\n\t{datetime.utcnow()}\n"

        # Adapter information
        message += f"Backends:\n\t{', '.join(self._adapters)}\n"

        # Machine information
        message += f"CPU\n\t{psutil.cpu_percent()}\n"
        message += f"Memory\n\t{psutil.virtual_memory().percent}\n"
        message += f"Memory Available\n\t{round(psutil.virtual_memory().available * 100 / psutil.virtual_memory().total, 2)}\n"
        message += f"Host\n\t{_HOSTNAME}\n"
        message += f"User\n\t{_USER}\n"

        # Process and thread information
        current_process = psutil.Process()
        message += f"PID\n\t{current_process.pid}\n"
        message += f"Active Threads\n\t{active_count()}\n"

        return Message(
            msg=message,
            channel=command.channel,
            backend=command.backend,
        )


class StatusCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = StatusCommand
