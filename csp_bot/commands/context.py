"""Command context for the new command framework.

Provides a typed, read-only view of a command invocation that both
decorator-based and class-based commands receive.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar, Union

from chatom import Channel, Message, User
from chatom.format import (
    FormattedAttachment,
    FormattedImage,
    FormattedMessage,
    Table,
    Text,
    TextNode,
    UserMention,
)

Deps = TypeVar("Deps")


class BotInfo:
    """Metadata about the bot instance."""

    __slots__ = ("id", "name", "version")

    def __init__(self, id: str = "", name: str = "", version: str = ""):
        self.id = id
        self.name = name
        self.version = version


class CommandContext(Generic[Deps]):
    """Typed, read-only view of a command invocation.

    Both ``@command`` decorated functions and ``Command`` subclasses
    receive this as their primary interface to the invocation.

    Attributes:
        command_name: The name of the command being executed.
        source: The user who invoked the command.
        targets: Users mentioned in the command arguments.
        channel: The channel where the command was issued.
        message: The original chatom Message.
        args: Parsed argument tokens (mentions stripped).
        args_text: Raw argument string.
        backend: Backend identifier ("slack", "symphony", etc.).
        bot: Bot metadata.
        deps: Injected dependencies.
    """

    __slots__ = (
        "command_name",
        "source",
        "targets",
        "channel",
        "message",
        "args",
        "args_text",
        "backend",
        "bot",
        "deps",
    )

    def __init__(
        self,
        *,
        command_name: str,
        source: User,
        targets: List[User],
        channel: Channel,
        message: Message,
        args: List[str],
        args_text: str,
        backend: str,
        bot: BotInfo,
        deps: Any = None,
    ):
        self.command_name = command_name
        self.source = source
        self.targets = targets
        self.channel = channel
        self.message = message
        self.args = args
        self.args_text = args_text
        self.backend = backend
        self.bot = bot
        self.deps = deps

    @property
    def target(self) -> Optional[User]:
        """First mentioned user, or None."""
        return self.targets[0] if self.targets else None

    def mention(self, user: Optional[User]) -> UserMention:
        """Create a mention node for a user.

        Args:
            user: The user to mention. Returns empty Text if None.

        Returns:
            A UserMention TextNode that renders correctly per backend.
        """
        if user is None:
            return UserMention(user_id="", display_name="")
        return UserMention(
            user_id=user.id,
            display_name=getattr(user, "display_name", "") or getattr(user, "name", "") or "",
        )

    def reply(self, *content: Union[TextNode, str, Table, FormattedImage, FormattedAttachment]) -> FormattedMessage:
        """Build a FormattedMessage from content nodes.

        Args:
            *content: Text nodes, strings, tables, images, or attachments.

        Returns:
            A FormattedMessage ready for rendering.

        Example:
            >>> ctx.reply(Bold(child=Text(content="Hello")), " world")
        """
        msg = FormattedMessage(metadata={"backend": self.backend})
        for item in content:
            if isinstance(item, str):
                msg.content.append(Text(content=item))
            else:
                msg.content.append(item)
        return msg

    def table(
        self,
        data: Any,
        headers: Optional[List[str]] = None,
        alignment: Optional[Union[str, List[str]]] = None,
    ) -> Table:
        """Build a Table node from data.

        Args:
            data: List of dicts, list of lists, or a pandas DataFrame.
            headers: Column headers (inferred from dicts/DataFrame if omitted).
            alignment: Column alignment ("left", "right", "center") or list per column.

        Returns:
            A Table node.
        """
        # Handle pandas DataFrame
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame):
                headers = headers or list(data.columns)
                data = data.values.tolist()
                return Table.from_data(data, headers=headers)
        except ImportError:
            pass

        # Handle list of dicts
        if data and isinstance(data[0], dict):
            return Table.from_dict_list(data, columns=headers)

        # Handle list of lists
        return Table.from_data(data, headers=headers)

    def image(
        self,
        url: str = "",
        alt: str = "",
        title: str = "",
        *,
        data: Optional[bytes] = None,
        filename: str = "",
        content_type: str = "",
    ) -> FormattedImage:
        """Create an image node.

        Provide either a ``url`` (the image is linked/unfurled) or raw
        ``data`` bytes (the image is uploaded to the chat via the backend's
        file-upload API).
        """
        return FormattedImage(
            url=url,
            alt_text=alt,
            title=title,
            data=data,
            filename=filename,
            content_type=content_type,
        )

    def attachment(
        self,
        url: str = "",
        filename: str = "",
        content_type: str = "",
        *,
        data: Optional[bytes] = None,
    ) -> FormattedAttachment:
        """Create an attachment node.

        Provide either a ``url`` or raw ``data`` bytes. When ``data`` is
        given the file is uploaded to the chat rather than linked.
        """
        return FormattedAttachment(url=url, filename=filename, content_type=content_type, data=data)
