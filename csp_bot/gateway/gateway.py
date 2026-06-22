"""Gateway module for csp-bot.

Provides the CSP Gateway integration with chatom-based bot.
"""

from functools import wraps
from logging import getLogger
from typing import Any, List, Union

from chatom import Message
from csp import ts
from csp_gateway import Controls
from csp_gateway.server import (
    Gateway as BaseGateway,
    GatewayChannels as GatewayChannelsBase,
    GatewayModule,
    GatewaySettings as BaseGatewaySettings,
)
from pydantic import Field, model_validator

from csp_bot import __version__
from csp_bot.commands import BaseCommandModel, CommandModel
from csp_bot.structs import BotCommand

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
    """Gateway channels for csp-bot.

    Uses chatom's Message type for unified message handling.
    """

    messages_in: ts[Message] = None
    """Incoming messages from all backends."""

    messages_out: ts[Message] = None
    """Outgoing messages to backends."""

    commands: ts[BotCommand] = None
    """Bot commands extracted from messages."""

    controls: ts[Controls] = None
    """Controls channel for graph admin."""


class GatewaySettings(BaseGatewaySettings):
    """Gateway settings for csp-bot."""

    TITLE: str = "CSP Bot"
    DESCRIPTION: str = "# Welcome to CSP Bot API\nREST/Websocket interfaces to CSP Gateway engine with chatom support."
    VERSION: str = __version__


class CspBotGateway(BaseGateway):
    """CSP Bot Gateway with chatom integration."""

    settings: GatewaySettings = Field(default_factory=GatewaySettings)
    commands: List[Union[BaseCommandModel, CommandModel]] = []
    deps: Any = None

    @model_validator(mode="before")
    @classmethod
    def _root_validate(cls, values):
        """Append user_commands to commands list."""
        if isinstance(values, dict):
            values["commands"] = values.get("commands") or []
            values["commands"].extend(values.pop("user_commands", []))
        return values

    def __hash__(self):
        return hash(id(self))

    def __init__(
        self,
        modules: List[GatewayModule] = None,
        channels: GatewayChannels = None,
        commands: List[Union[BaseCommandModel, CommandModel]] = None,
        deps: Any = None,
        *args,
        **kwargs,
    ):
        channels = channels or GatewayChannels()
        super().__init__(
            modules=modules,
            channels=channels,
            commands=commands,
            deps=deps,
            *args,
            **kwargs,
        )

        # Register commands with bot modules
        from csp_bot.bot import Bot

        log.info(f"Looking for Bot modules in {len(self.modules)} modules, commands to load: {len(self.commands)}")
        for module in self.modules:
            log.info(f"Checking module: {type(module).__name__} - is Bot: {isinstance(module, Bot)}")
            if isinstance(module, Bot):
                module.set_deps(self.deps)
                module.load_commands(self.commands)

    @wraps(BaseGateway.start)
    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)


# Convenience aliases
Channels = GatewayChannels
Gateway = CspBotGateway
Module = GatewayModule
Settings = GatewaySettings
