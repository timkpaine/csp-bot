from csp import Struct
from pydantic import BaseModel

__all__ = (
    "DiscordAdapterConfig",
    "DiscordAdapterManager",
    "DiscordMessage",
    "mention_user_discord",
)

try:
    from csp_adapter_discord import DiscordAdapterConfig, DiscordAdapterManager, DiscordMessage, mention_user as mention_user_discord
except ImportError:

    class DiscordAdapterConfig(BaseModel):
        pass

    DiscordAdapterManager = None

    class DiscordMessage(Struct):
        _ignore: str = ""

    mention_user_discord = lambda x: x  # noqa: E731
