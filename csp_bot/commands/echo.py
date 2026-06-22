"""Echo command for csp-bot.

A simple command that echoes back messages.
"""

from logging import getLogger
from typing import Optional, Type

from chatom import Message

from csp_bot.structs import BotCommand
from csp_bot.utils import mention_users

from .base import BaseCommand, BaseCommandModel, ReplyToOtherCommand

log = getLogger(__name__)


class EchoCommand(ReplyToOtherCommand):
    """Echo a message back to the channel."""

    def command(self) -> str:
        return "echo"

    def name(self) -> str:
        return "Echo"

    def help(self) -> str:
        return "Echo a message. Syntax: /echo <message> [/channel <channel>]"

    def execute(self, command: BotCommand) -> Optional[Message]:
        log.info(f"Echo command: {command.command}")

        # Build content from args
        content = " ".join(command.args) if command.args else ""

        # Add mentions for any tagged users
        if command.targets:
            mentions = mention_users(list(command.targets), command.backend)
            if mentions:
                content = f"{content} {mentions}".strip()

        # If nothing to echo (no args and no targets), return None
        if not content:
            return None

        return Message(
            content=content,
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class EchoCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = EchoCommand
