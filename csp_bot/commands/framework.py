"""New command framework for csp-bot.

Provides two APIs for defining commands:

1. ``@command`` decorator for stateless function-based commands
2. ``Command`` BaseModel subclass for stateful class-based commands

Both support four execution signatures: sync, async, generator, async generator.
The framework detects the signature automatically and handles async bridging,
generator draining, and error handling transparently.
"""

from __future__ import annotations

import logging
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
)

from ccflow import BaseModel

from csp_bot.commands.context import CommandContext

log = logging.getLogger(__name__)

_COMMAND_REGISTRY: Dict[str, "CommandEntry"] = {}


class CommandEntry:
    """Internal registry entry for a command."""

    __slots__ = ("name", "help", "backends", "handler", "is_class")

    def __init__(
        self,
        name: str,
        help: str,
        handler: Any,
        backends: Optional[List[str]] = None,
        is_class: bool = False,
    ):
        self.name = name
        self.help = help
        self.handler = handler
        self.backends = backends or []
        self.is_class = is_class


def command(
    name: str,
    help: str = "",
    backends: Optional[List[str]] = None,
) -> Callable:
    """Decorator to register a function as a bot command.

    The decorated function receives a ``CommandContext`` and returns
    a response. Four signatures are supported:

    - ``def f(ctx) -> T``: sync, single response
    - ``async def f(ctx) -> T``: async, single response
    - ``def f(ctx)``: sync generator, yields multiple responses
    - ``async def f(ctx)``: async generator, yields multiple responses

    Args:
        name: The command name (e.g. "echo" for /echo).
        help: Help text shown by the /help command.
        backends: List of backends this command supports. Empty = all.

    Returns:
        The original function, registered in the global command registry.

    Example::

        @command(name="echo", help="Echoes your message")
        def echo(ctx: CommandContext) -> str:
            return f"{ctx.mention(ctx.target)}: {ctx.args_text}"
    """

    def decorator(fn: Callable) -> Callable:
        entry = CommandEntry(
            name=name,
            help=help,
            handler=fn,
            backends=backends,
            is_class=False,
        )
        _COMMAND_REGISTRY[name] = entry
        # Stash metadata on the function for introspection
        fn._command_name = name
        fn._command_help = help
        fn._command_backends = backends or []
        return fn

    return decorator


def get_registered_commands() -> Dict[str, CommandEntry]:
    """Return a copy of the global command registry."""
    return dict(_COMMAND_REGISTRY)


def clear_registry() -> None:
    """Clear the global command registry. Intended for testing."""
    _COMMAND_REGISTRY.clear()


class Command(BaseModel):
    """Base class for stateful commands.

    Subclass this and implement ``execute`` to create a command that
    retains state across invocations. Fields are Pydantic-validated
    and composable with Hydra's ``_target_`` instantiation.

    ``execute`` supports all four signatures: sync, async, generator,
    async generator.

    Example::

        class MetsCommand(Command):
            name: str = "mets"
            help: str = "Show MLB standings"
            api_url: str = "https://..."

            def execute(self, ctx: CommandContext) -> str:
                return f"Standings from {self.api_url}"
    """

    name: str = ""
    """The command name (e.g. "mets" for /mets)."""

    help: str = ""
    """Help text shown by the /help command."""

    backends: List[str] = []
    """Backends this command supports. Empty = all."""

    def execute(self, ctx: CommandContext) -> Any:
        """Execute the command. Override in subclasses.

        Supports sync return, async return, sync generator (yield),
        and async generator (async yield).
        """
        raise NotImplementedError(f"{type(self).__name__} must implement execute()")


class CommandModel(BaseModel):
    """Hydra model for registering a Command subclass via config.

    Example YAML::

        mets:
          _target_: mypackage.MetsCommandModel
          command:
            _target_: mypackage.MetsCommand
            api_url: "https://..."
    """

    command: Type[Command] = Command
