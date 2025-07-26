from functools import wraps
from logging import getLogger
from typing import List

from csp import ts
from csp_gateway import (
    Controls,
    Gateway as BaseGateway,
    GatewayChannels as GatewayChannelsBase,
    GatewayModule,
    GatewaySettings as BaseGatewaySettings,
)
from pydantic import Field, root_validator

from csp_bot import __version__
from csp_bot.commands import BaseCommandModel
from csp_bot.structs import BotCommand, Message

log = getLogger(__name__)

__all__ = (
    "GatewayChannels",
    "GatewayModule",
    "GatewaySettings",
    "CspBotGateway",
    "Channels",
    "Gateway",
    "Module",
    "Settings",
)


class GatewayChannels(GatewayChannelsBase):
    messages_in: ts[Message] = None
    messages_out: ts[Message] = None
    commands: ts[BotCommand] = None
    controls: ts[Controls] = None
    """Channel for webserver/graph admin. """


class GatewaySettings(BaseGatewaySettings):
    # Override from csp-gateway
    TITLE: str = "CSP Bot"
    DESCRIPTION: str = "# Welcome to CSP Bot API\nContains REST/Websocket interfaces to underlying CSP Gateway engine"
    VERSION: str = __version__


class CspBotGateway(BaseGateway):
    settings: GatewaySettings = Field(default_factory=GatewaySettings)
    commands: List[BaseCommandModel] = []

    @root_validator(pre=True)
    def _root_validate(cls, values):
        """Root validator to append "user_commands" to list of commands."""
        values["commands"] = values.get("commands") or []
        values["commands"].extend(values.pop("user_commands", []))
        return values

    def __hash__(self):
        return hash(id(self))

    def __init__(
        self,
        modules: List[GatewayModule] = None,
        channels: GatewayChannels = None,
        commands: List[BaseCommandModel] = None,
        *args: str,
        **kwargs: str,
    ):
        # The normal initialization
        channels = channels or GatewayChannels()
        super().__init__(modules=modules, channels=channels, commands=commands, *args, **kwargs)

        # Register the commands, couldnt do from hydra easily
        from csp_bot.bot import Bot

        for module in self.modules:
            if isinstance(module, Bot):
                module.load_commands(self.commands)

    @wraps(BaseGateway.start)
    def start(self, *args, **kwargs):
        super(CspBotGateway, self).start(*args, **kwargs)


Channels = GatewayChannels
Gateway = CspBotGateway
Module = GatewayModule
Settings = GatewaySettings
