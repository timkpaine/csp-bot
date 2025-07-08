from html import escape
from logging import getLogger
from typing import TYPE_CHECKING, Mapping, Type

from croniter import CroniterBadCronError, croniter
from dateparser import parse

from csp_bot.structs import BotCommand, Message

from .base import BaseCommand, BaseCommandModel, ReplyCommand

if TYPE_CHECKING:
    from csp_bot import Bot

log = getLogger(__name__)


class ScheduleCommand(ReplyCommand):
    def command(self) -> str:
        return "schedule"

    def name(self) -> str:
        return "Schedule"

    def help(self) -> str:
        return (
            "Schedule a command. Syntax: /schedule [add, list, remove] [/schedule <5 or 6 column cron schedule. Use dashes or put in quotes>] "
            "[/delay <delay timedelta no spaces or in quotes, e.g. 5seconds, '5 hours', etc>] [bot command]"
        )

    def preexecute(
        self,
        command: BotCommand,
        schedule: Mapping[str, BotCommand],
        bot_instance: "Bot",
    ) -> BotCommand:
        log.info(f"Schedule command preexecute: {command}")

        remove = []

        if len(command.args) == 0:
            # assume list
            command.args = ("list",)

        if command.args[0] not in ("add", "list", "remove"):
            # malformed
            log.critical(f"Malformed schedule command: {command}")
            return

        if command.args[0] not in ("add", "remove"):
            # these don't need to be preexecuted
            return command

        # if adding, we need to parse and reform the command
        if command.args[0] in ("add", "remove"):
            # remove our schedule's command
            remove.append(0)

        if command.args[0] == "remove":
            # remove any args that satisfy
            for arg in command.args:
                schedule.pop(arg, None)

        if command.args[0] == "add":
            # parse through the arguments, pulling out the stuff that's specific to the schedule command
            for i, arg in enumerate(command.args):
                if i in remove:
                    # already handled, continue
                    continue

                if arg == "/schedule" and not hasattr(command, "schedule"):
                    remove.append(i)
                    if i + 1 >= len(command.args):
                        # malformed
                        log.critical("Schedule command preexecute: bad arg - schedule")
                    else:
                        # grab the cron string
                        try:
                            # try to parse it
                            schedule_string = command.args[i + 1].replace("-", " ")
                            croniter(schedule_string)

                            # attach if the previous command passed
                            command.schedule = schedule_string

                            # remove this arg
                            remove.append(i + 1)
                        except CroniterBadCronError:
                            # don't remove it in this case
                            ...

                if arg == "/delay" and not hasattr(command, "delay"):
                    remove.append(i)
                    if i + 1 >= len(command.args):
                        # malformed
                        log.critical("Schedule command preexecute: bad arg - delay")
                    else:
                        # grab the delay string
                        delay = parse(
                            command.args[i + 1], settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "EST", "TO_TIMEZONE": "UTC"}
                        )  # TODO handle local timezone properly
                        if delay:
                            # attach if the previous command passed
                            command.delay = delay

                            # remove this arg
                            remove.append(i + 1)
                        else:
                            # don't remove it in this case
                            ...

            # now reformulate the args, removing the ones that we used for the schedule command
            command.args = tuple([arg for i, arg in enumerate(command.args) if i not in remove])

            # now we need to replace command.command itself, so lets re-parse the command args, so reparse the tokens
            new_command, new_command_args, _, _ = bot_instance.bot_commands_from_command_string(command.args, command.message, "")
            command.command = new_command
            command.args = tuple(new_command_args)
            return command

    def execute(self, command: BotCommand, schedule: Mapping[str, BotCommand]) -> Message:
        log.info(f"Schedule command: {command}")
        table = "<table><thead><tr><td>ID</td><td>Command</td></tr></thead><tbody>"
        for command in schedule.values():
            table += f"<tr><td>{command.id}</td><td>{escape(str(command.to_dict()))}</td></tr>"
        table += "</tbody></table>"
        message = f'<expandable-card state="collapsed"><header>Bot Schedule</header><body variant="default">{table}</body></expandable-card>'
        return Message(
            msg=message,
            channel=command.channel,
            backend=command.backend,
        )


class ScheduleCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = ScheduleCommand
