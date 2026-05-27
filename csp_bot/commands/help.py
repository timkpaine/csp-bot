"""Help command for csp-bot.

Uses chatom's formatting utilities for cross-platform output.
"""

from html import escape
from logging import getLogger
from typing import Mapping, Optional, Type

from chatom import Message

from csp_bot.structs import BotCommand

from .base import BaseCommand, BaseCommandModel, ReplyCommand

log = getLogger(__name__)


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
        commands: Mapping[str, "BaseCommand"] = None,
    ) -> Optional[Message]:
        log.info(f"Help command: {command.command}")

        # Collect help for each command
        helps = []
        for cmd_key, cmd_inst in commands.items():
            # Skip hidden commands
            if cmd_key.startswith("_"):
                continue

            # Skip commands not supported on this backend
            if cmd_inst.backends() and command.backend not in cmd_inst.backends():
                continue

            # Filter by requested commands if args provided
            if command.args and cmd_key not in command.args:
                continue

            helps.append(
                (
                    escape(cmd_key, quote=True),
                    escape(cmd_inst.name(), quote=True),
                    escape(cmd_inst.help(), quote=True),
                )
            )

        helps = sorted(helps, key=lambda x: x[0])

        # Build response using chatom's FormattedMessage
        if command.backend == "symphony":
            # Symphony supports expandable cards
            table = "<table><thead><tr><td>Command</td><td>Name</td><td>Info</td></tr></thead><tbody>"
            for cmd_key, name, help_text in helps:
                table += f"<tr><td>/{cmd_key}</td><td>{name}</td><td>{help_text}</td></tr>"
            table += "</tbody></table>"
            content = f'<expandable-card state="collapsed"><header>Bot Commands Help</header><body variant="default">{table}</body></expandable-card>'
        elif command.backend == "slack":
            # Slack uses mrkdwn code blocks for tables
            lines = ["*Bot Commands Help*", "```"]
            lines.append(f"{'Command':<15} {'Name':<15} {'Info'}")
            lines.append("-" * 60)
            for cmd_key, name, help_text in helps:
                lines.append(f"/{cmd_key:<14} {name:<15} {help_text}")
            lines.append("```")
            content = "\n".join(lines)
        elif command.backend == "discord":
            # Discord uses markdown tables
            lines = ["# Bot Commands Help", ""]
            lines.append("| Command | Name | Info |")
            lines.append("|---------|------|------|")
            for cmd_key, name, help_text in helps:
                lines.append(f"| /{cmd_key} | {name} | {help_text} |")
            content = "\n".join(lines)
        elif command.backend == "telegram":
            # Telegram uses HTML formatting
            lines = ["<b>Bot Commands Help</b>", ""]
            for cmd_key, name, help_text in helps:
                lines.append(f"/{cmd_key} — <b>{name}</b>: {help_text}")
            content = "\n".join(lines)
        else:
            # Plain text fallback
            lines = ["Bot Commands Help", ""]
            for cmd_key, name, help_text in helps:
                lines.append(f"/{cmd_key}: {name} - {help_text}")
            content = "\n".join(lines)

        return Message(
            content=content,
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class HelpCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = HelpCommand
