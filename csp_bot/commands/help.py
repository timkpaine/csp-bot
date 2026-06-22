"""Help command for csp-bot.

Uses chatom's FormattedMessage for automatic cross-platform rendering.
"""

from logging import getLogger
from typing import Any, Mapping, Optional, Type

from chatom import Message
from chatom.format import FormattedMessage, Heading, Table, Text

from csp_bot.structs import BotCommand

from .base import BaseCommand, BaseCommandModel, ReplyCommand

log = getLogger(__name__)


def _command_backends(runner: Any) -> list:
    """Get backends list from either legacy or new command types."""
    if isinstance(runner, BaseCommand):
        return runner.backends()
    return getattr(runner, "backends", []) or []


def _command_name(runner: Any) -> str:
    if isinstance(runner, BaseCommand):
        return runner.name()
    return getattr(runner, "name", "") or ""


def _command_help(runner: Any) -> str:
    if isinstance(runner, BaseCommand):
        return runner.help()
    return getattr(runner, "help", "") or ""


class HelpCommand(ReplyCommand):
    """Display help for available commands."""

    def command(self) -> str:
        return "help"

    def name(self) -> str:
        return "Help"

    def help(self) -> str:
        return "Get help with bot commands. Syntax: /help [command]"

    def execute(
        self,
        command: BotCommand,
        commands: Mapping[str, Any] = None,
    ) -> Optional[Message]:
        log.info(f"Help command: {command.command}")

        # Collect help for each command
        rows = []
        for cmd_key, cmd_inst in commands.items():
            if cmd_key.startswith("_"):
                continue

            backends = _command_backends(cmd_inst)
            if backends and command.backend not in backends:
                continue

            if command.args and cmd_key not in command.args:
                continue

            rows.append(
                {
                    "Command": f"/{cmd_key}",
                    "Name": _command_name(cmd_inst),
                    "Info": _command_help(cmd_inst),
                }
            )

        rows.sort(key=lambda r: r["Command"])

        msg = FormattedMessage(metadata={"backend": command.backend})
        msg.content.append(Heading(child=Text(content="Bot Commands Help"), level=3))
        msg.content.append(Table.from_dict_list(rows, columns=["Command", "Name", "Info"]))

        return Message(
            content=msg.render_for(command.backend),
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class HelpCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = HelpCommand
