"""Schedule command for csp-bot.

Allows scheduling commands for delayed or recurring execution.
"""

from html import escape
from logging import getLogger
from typing import TYPE_CHECKING, List, Mapping, Optional, Type

from chatom import Message
from croniter import CroniterBadCronError, croniter
from dateparser import parse

from csp_bot.structs import BotCommand

from .base import BaseCommand, BaseCommandModel, ReplyCommand

if TYPE_CHECKING:
    from csp_bot import Bot

log = getLogger(__name__)


class ScheduleCommand(ReplyCommand):
    """Schedule commands for delayed or recurring execution."""

    def command(self) -> str:
        return "schedule"

    def name(self) -> str:
        return "Schedule"

    def help(self) -> str:
        return "Schedule a command. Syntax: /schedule [add, list, remove] [/schedule <cron>] [/delay <time>] [bot command]"

    def preexecute(
        self,
        command: BotCommand,
        schedule: Mapping[str, BotCommand],
        bot_instance: "Bot",
    ) -> Optional[BotCommand]:
        log.info(f"Schedule command preexecute: {command.command}")

        remove: List[int] = []

        if not command.args:
            command.args = ("list",)

        if command.args[0] not in ("add", "list", "remove"):
            log.warning(f"Invalid schedule subcommand: {command.args[0]}")
            return None

        if command.args[0] not in ("add", "remove"):
            return command

        if command.args[0] in ("add", "remove"):
            remove.append(0)

        if command.args[0] == "remove":
            for arg in command.args[1:]:
                schedule.pop(arg, None)
            return None

        if command.args[0] == "add":
            args = list(command.args)

            for i, arg in enumerate(args):
                if i in remove:
                    continue

                if arg == "/schedule":
                    remove.append(i)
                    if i + 1 < len(args):
                        try:
                            schedule_string = args[i + 1].replace("-", " ")
                            croniter(schedule_string)
                            command.schedule = schedule_string
                            remove.append(i + 1)
                        except CroniterBadCronError:
                            log.warning(f"Invalid cron: {args[i + 1]}")

                if arg == "/delay":
                    remove.append(i)
                    if i + 1 < len(args):
                        delay = parse(
                            args[i + 1],
                            settings={
                                "PREFER_DATES_FROM": "future",
                                "TIMEZONE": "EST",
                                "TO_TIMEZONE": "UTC",
                            },
                        )
                        if delay:
                            command.delay = delay
                            remove.append(i + 1)

            # Rebuild args without schedule-specific tokens
            new_args = [arg for i, arg in enumerate(args) if i not in remove]
            command.args = tuple(new_args)

            # Re-parse the inner command
            if new_args:
                inner_cmd = new_args[0].lstrip("/")
                command.command = inner_cmd
                command.args = tuple(new_args[1:])

            return command

        return None

    def execute(self, command: BotCommand, schedule: Mapping[str, BotCommand]) -> Message:
        log.info("Schedule list command")

        # Build schedule listing
        if command.backend == "symphony":
            table = "<table><thead><tr><td>ID</td><td>Command</td></tr></thead><tbody>"
            for scheduled_cmd in schedule.values():
                table += f"<tr><td>{id(scheduled_cmd)}</td><td>{escape(scheduled_cmd.command)}</td></tr>"
            table += "</tbody></table>"
            content = f'<expandable-card state="collapsed"><header>Bot Schedule</header><body variant="default">{table}</body></expandable-card>'
        else:
            lines = ["*Scheduled Commands*", ""]
            for scheduled_cmd in schedule.values():
                lines.append(f"- {id(scheduled_cmd)}: /{scheduled_cmd.command}")
            content = "\n".join(lines)

        return Message(
            content=content,
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class ScheduleCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = ScheduleCommand
