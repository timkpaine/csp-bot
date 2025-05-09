from html import escape, unescape
from logging import getLogger
from typing import Mapping, Type

import pandas as pd

from csp_bot.structs import BotCommand, Message

from .base import BaseCommand, BaseCommandModel, ReplyCommand

log = getLogger(__name__)


class HelpCommand(ReplyCommand):
    def command(self) -> str:
        return "help"

    def name(self) -> str:
        return "Help"

    def help(self) -> str:
        return "Get Help with a Bot Command. Syntax: /help [command]"

    def execute(
        self,
        command: BotCommand,
        commands: Mapping[str, "BaseCommand"] = None,
    ) -> Message:
        log.info(f"Help command: {command}")

        helps = []

        for command_key, command_inst in commands.items():
            # Omit hidden commands
            if command_key.startswith("_"):
                continue
            # Omit commands that are not supported for this backend
            if command_inst.backends() and command.backend not in command_inst.backends():
                continue
            if len(set(command.args).intersection(commands.keys())) == 0 or command_key in command.args:
                # Grab extra stuff
                name = command_inst.name()
                help = command_inst.help()
                helps.append(
                    (
                        escape(command_key, quote=True),
                        escape(name, quote=True),
                        escape(help, quote=True),
                    )
                )

        helps = sorted(helps, key=lambda x: x[0])
        if command.backend == "symphony":
            table = "<table><thead><tr><td>Command</td><td>Name</td><td>Info</td></tr></thead><tbody>"
            for command_key, name, help in helps:
                table += f"<tr><td>/{command_key}</td><td>{name}</td><td>{help}</td></tr>"
            table += "</tbody></table>"
            message = f'<expandable-card state="collapsed"><header>Bot Commands Help</header><body variant="default">{table}</body></expandable-card>'
        elif command.backend == "slack":
            table = pd.DataFrame(helps, columns=["Command", "Name", "Info"]).to_markdown(index=False)
            message = f"Bot Commands Help\n```\n{table}\n```"
        elif command.backend == "discord":
            table = unescape(pd.DataFrame(helps, columns=["Command", "Name", "Info"]).to_markdown(index=False))
            message = f"# Bot Commands Help\n{table}"
        else:
            raise NotImplementedError(f"Unsupported backend: {command.backend}")

        return Message(
            msg=message,
            channel=command.channel,
            backend=command.backend,
        )


class HelpCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = HelpCommand
