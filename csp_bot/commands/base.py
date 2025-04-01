from abc import ABC, abstractmethod
from typing import List, Type, Union

from ccflow import BaseModel

from csp_bot.structs import Backend, BotCommand, CommandVariant, Message


class BaseCommand(ABC):
    @staticmethod
    @abstractmethod
    def kind() -> CommandVariant: ...

    @staticmethod
    def backends() -> List[Backend]:
        """Returns a list of supported backends. NOTE: empty implies all backends."""
        return []

    @abstractmethod
    def command(self) -> str:
        """Signature of the command, used for /{command} in symphony

        Returns:
            str: command signature
        """

    @abstractmethod
    def name(self) -> str:
        """Name of the command, used for help / info

        Returns:
            str: name of the command
        """

    @abstractmethod
    def help(self) -> str:
        """Help string for the command

        Returns:
            str: The help text, plain formatted.
        """

    @abstractmethod
    def num_recipients(self) -> int:
        """How many users this command can tag

        Returns:
            int: 0 for no tagging, 1 for single target, any other number for any number of tags
        """

    def preexecute(self, command: BotCommand) -> BotCommand:
        return command

    @abstractmethod
    def execute(
        self,
        command: BotCommand,
    ) -> Union[Message, List[Message], "BaseCommand", List["BaseCommand"]]:
        return []


class NoResponseCommand(BaseCommand):
    @staticmethod
    def kind() -> CommandVariant:
        return CommandVariant.NO_RESPONSE

    def num_recipients(self) -> int:
        return 0


class ReplyCommand(BaseCommand):
    @staticmethod
    def kind() -> CommandVariant:
        return CommandVariant.REPLY

    def num_recipients(self) -> int:
        return 0


class ReplyToAuthorCommand(BaseCommand):
    @staticmethod
    def kind() -> CommandVariant:
        return CommandVariant.REPLY_TO_AUTHOR

    def num_recipients(self) -> int:
        return 1


class ReplyToOtherCommand(BaseCommand):
    @staticmethod
    def kind() -> CommandVariant:
        return CommandVariant.REPLY_TO_OTHER

    def num_recipients(self) -> int:
        return 1


class ReplyToAllCommand(BaseCommand):
    @staticmethod
    def kind() -> CommandVariant:
        return CommandVariant.REPLY_TO_ALL

    def num_recipients(self) -> int:
        return -1


class BaseCommandModel(BaseModel):
    command: Type[BaseCommand]
