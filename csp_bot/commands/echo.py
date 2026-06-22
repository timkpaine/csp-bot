"""Echo command for csp-bot.

A simple command that echoes back messages using FormattedMessage.
"""

from logging import getLogger
from typing import Optional, Type

from chatom import Message
from chatom.format import FormattedMessage, Text, UserMention

from csp_bot.structs import BotCommand

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

        text = " ".join(command.args) if command.args else ""
        has_targets = bool(command.targets)

        if not text and not has_targets:
            return None

        msg = FormattedMessage(metadata={"backend": command.backend})
        if text:
            msg.content.append(Text(content=text))
        for target in command.targets:
            if msg.content:
                msg.content.append(Text(content=" "))
            msg.content.append(
                UserMention(
                    user_id=target.id,
                    display_name=getattr(target, "display_name", "") or getattr(target, "name", "") or "",
                )
            )

        return Message(
            content=msg.render_for(command.backend),
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class EchoCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = EchoCommand
