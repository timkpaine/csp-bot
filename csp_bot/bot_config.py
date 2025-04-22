from typing import List, Optional, Union

from ccflow import BaseModel
from pydantic import Field

from .backends import DiscordAdapterConfig, SlackAdapterConfig, SymphonyAdapterConfig

__all__ = (
    "BaseConfig",
    "BotConfig",
    "DiscordConfig",
    "SlackConfig",
    "SymphonyConfig",
)


class BaseConfig(BaseModel):
    bot_name: str = Field(description="Name of the bot as displayed")
    adapter_config: Union[DiscordAdapterConfig, SlackAdapterConfig, SymphonyAdapterConfig]

    user_access_channels: List[str] = Field(
        [],
        description="If non-empty, only users from these channels can interact with the bot. However, they can interact with the bot in any channel.",
    )
    query_user_access_channels_seconds: int = Field(
        300, description="How frequently to query the 'user_access_channels' for a list of allowed users. If 0, this is only queried once at startup."
    )
    unauthorized_msg: Optional[str] = Field(
        "You are not authorized to interact with this bot.",
        description="What message to send (if any) when an unauthorized user attempts to interact with the bot. This is only relevant if 'user_access_channels' is set. If None, no message is sent.",
    )

    def adapter_kwargs(self):
        return {}


class DiscordConfig(BaseConfig):
    adapter_config: DiscordAdapterConfig


class SlackConfig(BaseConfig):
    adapter_config: SlackAdapterConfig


class SymphonyConfig(BaseConfig):
    adapter_config: SymphonyAdapterConfig
    exit_msg: str = ""
    initial_rooms: List[str] = []
    allow_new_rooms: bool = True
    set_presence_seconds: int = Field(
        0,
        description="How many seconds to wait between periods of sending requests to set prescence as AVAILABLE. If 0, presence is never set. Calling this endpoint requires the ADMIN_PRESENCE_UPDATE privilege. According to the Symphony docs, after 5 minutes of inactivity, a user turns from AVAILABLE to AWAY, if still connected to symphony. Otherwise, OFFLINE",
    )

    def adapter_kwargs(self):
        return {
            "exit_msg": self.exit_msg,
            "rooms": set(self.initial_rooms),
        }


class BotConfig(BaseModel):
    discord_config: Optional[DiscordConfig] = None
    slack_config: Optional[SlackConfig] = None
    symphony_config: Optional[SymphonyConfig] = None

    ratelimit_seconds: int = 1
