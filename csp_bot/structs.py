from datetime import datetime
from enum import Enum
from typing import Tuple, Union

from csp import Struct
from csp_gateway.utils.struct import GatewayStruct

from .backends import DiscordMessage as BaseDiscordMessage, SlackMessage as BaseSlackMessage, SymphonyMessage as BaseSymphonyMessage
from .utils import Backend

__all__ = (
    "Backend",
    "CommandVariant",
    "Message",
    "User",
    "BotCommand",
)


class CommandVariant(Enum):
    # No response needed, used when you want
    # the bot to go and trigger something else
    # without replying via symphony
    NO_RESPONSE = 0

    # User will @ the bot, and the bot
    # will respond, optionally in a given
    # room
    REPLY = 1

    # User will @ the bot, and the bot
    # will reply to the user @ing them
    # back, optionally in a given room
    REPLY_TO_AUTHOR = 2

    # User will @ the bot and another
    # user, and the bot will @ the
    # tagged user, optionally in a given
    # room
    REPLY_TO_OTHER = 3

    # User will @ the bot and any
    # number of other users, and the
    # bot will reply to all excluding
    # the bot itself, optionall in a
    # given room
    REPLY_TO_ALL = 4


class Message(GatewayStruct):
    user: str
    """username of the user, specific to the platform"""

    user_email: str
    """email of the author, for mentions"""

    user_id: str
    """uid of the author, for mentions, specific to the platform"""

    tags: [str]
    """list of user ids in message, for mentions"""

    msg: str
    """plain text payload of the message"""

    reaction: str
    """emote, for backends that support emote reactions"""

    thread: str
    """thread id, for backends that support threads"""

    channel: str
    """name of channel/room"""

    backend: str
    """Backend, e.g. slack, symphony, discord"""

    _raw: object
    """raw message payload, private to avoid serialization"""

    @staticmethod
    def from_raw_message(adapter_type: str, msg: Union[BaseDiscordMessage, BaseSlackMessage, BaseSymphonyMessage]) -> "Message":
        ret = Message()
        ret.user = msg.user if hasattr(msg, "user") else ""
        ret.user_email = msg.user_email if hasattr(msg, "user_email") else ""
        ret.user_id = msg.user_id if hasattr(msg, "user_id") else ""
        ret.tags = msg.tags if hasattr(msg, "tags") else []
        ret.msg = msg.msg if hasattr(msg, "msg") else ""
        ret.backend = adapter_type
        ret._raw = msg
        if adapter_type == "symphony":
            ret.channel = msg.room if msg.room != "DM" else msg.room_id
            # not supported
            ret.reaction = ""
            ret.thread = ""
        elif adapter_type == "slack":
            ret.channel = msg.channel if msg.channel != "DM" else msg.channel_id
            ret.reaction = msg.reaction if hasattr(msg, "reaction") else ""
            ret.thread = msg.thread if hasattr(msg, "thread") else ""
        elif adapter_type == "discord":
            ret.channel = msg.channel if msg.channel != "DM" else msg.channel_id
            ret.reaction = msg.reaction if hasattr(msg, "reaction") else ""
            ret.thread = msg.thread if hasattr(msg, "thread") else ""
        else:
            raise NotImplementedError(f"Adapter type {adapter_type} not supported")
        return ret

    def to_raw_message(self, adapter_type: str) -> Union[BaseDiscordMessage, BaseSlackMessage, BaseSymphonyMessage]:
        if adapter_type == "symphony":
            return BaseSymphonyMessage(
                user=self.user if hasattr(self, "user") else "",
                user_email=self.user_email if hasattr(self, "user_email") else "",
                user_id=self.user_id if hasattr(self, "user_id") else "",
                tags=self.tags.copy() if hasattr(self, "tags") else [],
                room=self.channel if hasattr(self, "channel") else "",
                msg=self.msg if hasattr(self, "msg") else "",
                form_values=self.payload.copy() if hasattr(self, "payload") else {},
            )
        elif adapter_type == "slack":
            return BaseSlackMessage(
                user=self.user if hasattr(self, "user") else "",
                user_email=self.user_email if hasattr(self, "user_email") else "",
                user_id=self.user_id if hasattr(self, "user_id") else "",
                tags=self.tags.copy() if hasattr(self, "tags") else [],
                channel=self.channel if hasattr(self, "channel") else "",
                msg=self.msg if hasattr(self, "msg") else "",
                reaction=self.reaction if hasattr(self, "reaction") else "",
                thread=self.thread if hasattr(self, "thread") else "",
                payload=self.payload.copy() if hasattr(self, "payload") else {},
            )
        elif adapter_type == "discord":
            return BaseDiscordMessage(
                user=self.user if hasattr(self, "user") else "",
                user_email=self.user_email if hasattr(self, "user_email") else "",
                user_id=self.user_id if hasattr(self, "user_id") else "",
                tags=self.tags.copy() if hasattr(self, "tags") else [],
                channel=self.channel if hasattr(self, "channel") else "",
                msg=self.msg if hasattr(self, "msg") else "",
                reaction=self.reaction if hasattr(self, "reaction") else "",
                thread=self.thread if hasattr(self, "thread") else "",
                payload=self.payload.copy() if hasattr(self, "payload") else None,
            )
        else:
            raise NotImplementedError(f"Adapter type {adapter_type} not supported")


class User(Struct):
    id: str
    name: str
    backend: str  # TODO: Backend


class BotCommand(GatewayStruct):
    message: Message
    command: str
    args: Tuple[str]
    source: User
    targets: Tuple[User]

    channel: str
    backend: str  # TODO: Backend

    variant: CommandVariant

    delay: datetime  # NOTE: this is a datetime type because we use dateparser
    schedule: str
    times_run: int = 0


BotCommand.omit_from_lookup()
Message.omit_from_lookup()
