from logging import getLogger
from typing import Optional, Type

from csp_bot.structs import BotCommand, Message

from .base import BaseCommand, BaseCommandModel, ReplyToOtherCommand

log = getLogger(__name__)


class EchoCommand(ReplyToOtherCommand):
    def command(self) -> str:
        return "echo"

    def name(self) -> str:
        return "echo"

    def help(self) -> str:
        return "Echo something. Syntax: /echo <message> [/channel <channel>]"

    def execute(self, command: BotCommand) -> Optional[Message]:
        log.info(f"Echo command: {command}")

        if not command.args:
            # Malformed
            return
        message = " ".join(command.args)
        return Message(
            msg=message,
            channel=command.channel,
            backend=command.backend,
        )


class EchoCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = EchoCommand
