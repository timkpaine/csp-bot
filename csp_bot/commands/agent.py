"""AgentCommand — base class for LLM-powered bot commands.

Provides the boilerplate for running a pydantic-ai Agent from within
a csp-bot command: background execution via a thread pool, automatic
rescheduling until the LLM call completes, and formatted response output.

Supports **stateful sessions**: when a user replies to a bot response (or
invokes the same command again within a time window), the conversation
history is resumed automatically.  Sessions expire after a configurable TTL.

Subclasses implement :meth:`build_agent` and :meth:`build_prompt`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from abc import abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Union

from chatom import Channel, Message
from chatom.backend import BackendBase
from chatom.format import Format, convert_format

from csp_bot.commands.base import BaseCommand, ReplyCommand
from csp_bot.structs import BotCommand

try:
    from chatom.agent import BackendToolset
    from chatom.agent.toolset import AccessPolicy
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage
except ImportError as e:
    raise ImportError("AgentCommand requires the 'agent' extra. Install with: pip install csp-bot[agent]") from e

log = logging.getLogger(__name__)

__all__ = ("AgentCommand",)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-cmd")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentSession:
    """Tracks a multi-turn conversation between a user and an agent command."""

    user_id: str
    channel_id: str
    command_name: str
    message_history: List[ModelMessage] = field(default_factory=list)
    last_active: datetime = field(default_factory=_utc_now)
    bot_response_id: Optional[str] = None  # ID of last bot message (for reply matching)

    def touch(self) -> None:
        self.last_active = _utc_now()

    def is_expired(self, ttl_seconds: float) -> bool:
        return (_utc_now() - self.last_active).total_seconds() > ttl_seconds


class SessionStore:
    """Thread-safe store for agent sessions with automatic expiry."""

    def __init__(self, ttl_seconds: float = 900.0):
        self._sessions: Dict[str, AgentSession] = {}
        self._response_index: Dict[str, str] = {}  # bot_response_id -> session_key
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[AgentSession]:
        with self._lock:
            session = self._sessions.get(key)
            if session and session.is_expired(self._ttl):
                self._remove_session(key)
                return None
            return session

    def get_by_response_id(self, response_id: str) -> Optional[AgentSession]:
        """Look up a session by the bot's response message ID (for replies)."""
        with self._lock:
            key = self._response_index.get(response_id)
            if key is None:
                return None
            session = self._sessions.get(key)
            if session and session.is_expired(self._ttl):
                self._remove_session(key)
                return None
            return session

    def put(self, key: str, session: AgentSession) -> None:
        with self._lock:
            self._sessions[key] = session
            if session.bot_response_id:
                self._response_index[session.bot_response_id] = key

    def update_response_id(self, key: str, response_id: str) -> None:
        """Associate a bot response message ID with a session."""
        with self._lock:
            session = self._sessions.get(key)
            if session:
                # Remove old mapping
                if session.bot_response_id and session.bot_response_id in self._response_index:
                    del self._response_index[session.bot_response_id]
                session.bot_response_id = response_id
                self._response_index[response_id] = key

    def _remove_session(self, key: str) -> None:
        """Remove a session (caller must hold lock)."""
        session = self._sessions.pop(key, None)
        if session and session.bot_response_id:
            self._response_index.pop(session.bot_response_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        with self._lock:
            expired = [k for k, s in self._sessions.items() if s.is_expired(self._ttl)]
            for key in expired:
                self._remove_session(key)
            return len(expired)


def _run_agent(
    agent: Agent,
    prompt: Union[str, Sequence[Any]],
    loop: Optional[asyncio.AbstractEventLoop] = None,
    message_history: Optional[Sequence[ModelMessage]] = None,
) -> Any:
    """Run an agent on an event loop (for use in thread pool).

    If *loop* is provided (i.e. the backend's event loop), it is reused so
    that aiohttp sessions bound to it remain valid.  Otherwise a fresh loop
    is created.

    ``prompt`` may be a plain string or a sequence of pydantic-ai user
    content parts (e.g. text plus :class:`~pydantic_ai.BinaryContent`
    images), enabling multimodal input.
    """
    coro = agent.run(prompt, message_history=message_history)
    if loop is not None and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    owns_loop = loop is None
    if owns_loop:
        loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        if owns_loop:
            loop.close()


class AgentCommand(ReplyCommand):
    """Base class for commands that run a pydantic-ai agent with session support.

    Subclasses implement :meth:`build_agent` and :meth:`build_prompt`,
    and receive a :class:`~chatom.agent.BackendToolset` for free via
    :meth:`build_toolset`.

    **Session continuity**: conversation history is preserved per
    user+channel+command.  If the user replies to the bot's response
    (thread reply or message reference), the prior session is resumed.
    Sessions expire after :attr:`session_ttl_seconds`.

    Example::

        class AskCommand(AgentCommand):
            def command(self): return "ask"
            def name(self): return "Ask"
            def help(self): return "/ask <question> — Ask the AI (reply to continue)"

            def build_agent(self, command):
                toolset = self.build_toolset(command)
                return Agent(
                    "anthropic:claude-sonnet-4-6",
                    toolsets=[toolset] if toolset else [],
                    instructions="You are a helpful assistant.",
                )

            def build_prompt(self, command):
                return " ".join(command.args)
    """

    _backends: ClassVar[Dict[str, BackendBase]] = {}
    _backend_loops: ClassVar[Dict[str, asyncio.AbstractEventLoop]] = {}
    _futures: ClassVar[Dict[str, Future]] = {}
    _sessions: ClassVar[SessionStore] = SessionStore(ttl_seconds=900.0)

    # Configurable delay between polling checks (seconds)
    poll_interval: int = 2
    # Maximum time to wait for agent completion (seconds)
    timeout: int = 120
    # Session time-to-live (seconds). 0 disables sessions.
    session_ttl_seconds: float = 900.0
    # Send a status message every N poll cycles (0 disables)
    status_every_n_polls: int = 15
    # When True, image attachments on the incoming message are downloaded
    # and passed to the model as multimodal input (so the agent can "see"
    # images the user posted).
    include_incoming_images: bool = True
    # Maximum size (bytes) of an incoming image to download for the model.
    max_incoming_image_bytes: int = 5_000_000
    # Status messages shown to the user while processing
    status_messages: ClassVar[List[str]] = [
        "Thinking...",
        "Still working on it...",
        "Processing your request...",
        "Almost there...",
        "Crunching the data...",
    ]

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def set_backends(
        cls,
        backends: Dict[str, BackendBase],
        loops: Optional[Dict[str, asyncio.AbstractEventLoop]] = None,
    ) -> None:
        """Inject backend instances. Called by Bot after adapter setup."""
        cls._backends = backends
        cls._backend_loops = loops or {}

    @classmethod
    def set_session_ttl(cls, ttl_seconds: float) -> None:
        """Reconfigure the session TTL."""
        cls._sessions = SessionStore(ttl_seconds=ttl_seconds)

    @abstractmethod
    def build_agent(self, command: BotCommand) -> Agent:
        """Return the pydantic-ai Agent to run for this command."""
        ...

    @abstractmethod
    def build_prompt(self, command: BotCommand) -> str:
        """Return the user prompt string."""
        ...

    def build_toolset(self, command: BotCommand) -> Optional[BackendToolset]:
        """Return a BackendToolset for the command's backend, or None.

        The toolset is configured with an AccessPolicy that enforces:
        - The agent can only access the channel where the command was invoked
        - The requesting user must be a member of any target channel
        - DM reads are blocked by default
        - Message count is capped per request

        Subclasses can override :meth:`build_access_policy` to customize.
        """
        backend = self._backends.get(command.backend)
        if backend is None:
            return None
        policy = self.build_access_policy(command)
        return BackendToolset(backend=backend, access_policy=policy)

    def build_access_policy(self, command: BotCommand) -> "AccessPolicy":
        """Build the access policy for this command invocation.

        Override in subclasses to customize access rules. The default
        policy restricts access to the channel where the user typed the
        command (not the /room redirect target).
        """
        # Use the original channel where the user issued the command,
        # not the /room-redirected destination.
        origin_channel_id = command.message.channel_id if command.message and command.message.channel_id else command.channel_id
        return AccessPolicy(
            requesting_user=command.source,
            invoking_channel_id=origin_channel_id,
            restrict_to_invoking_channel=True,
            require_membership=True,
            block_dm_reads=True,
        )

    def get_model(self, model_name: str = "claude-sonnet-4-6") -> Any:
        """Return a model instance configured from environment variables.

        Checks ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL
        to construct a properly-configured provider.
        """
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        base_url = os.environ.get("ANTHROPIC_BASE_URL")

        provider = AnthropicProvider(api_key=api_key, base_url=base_url)
        return AnthropicModel(model_name, provider=provider)

    def wrap_symphony_output(self, messageml: str, command: BotCommand) -> str:
        """Hook to post-process Symphony MessageML before wrapping in <messageML>.

        Override in subclasses to wrap output in expandable cards, add
        headers, etc. Default is identity (no wrapping).
        """
        return messageml

    def _session_key(self, command: BotCommand) -> str:
        """Key for session lookup: command:user:channel."""
        return f"{self.command()}:{command.source.id}:{command.channel_id}"

    def _get_session(self, command: BotCommand) -> Optional[AgentSession]:
        """Find an existing session — by reply reference or by user+channel."""
        # First: check if this is a reply to a bot message
        msg = command.message
        reply_to_id = getattr(msg, "reply_to_id", None) or (msg.reference.message_id if getattr(msg, "reference", None) else None)
        if reply_to_id:
            session = self._sessions.get_by_response_id(reply_to_id)
            if session:
                session.touch()
                return session

        # Second: check by user+channel (same command re-invoked)
        session = self._sessions.get(self._session_key(command))
        if session:
            session.touch()
            return session

        return None

    def _create_session(self, command: BotCommand) -> AgentSession:
        """Create a new session for this command invocation."""
        session = AgentSession(
            user_id=command.source.id,
            channel_id=command.channel_id,
            command_name=self.command(),
        )
        self._sessions.put(self._session_key(command), session)
        return session

    def _command_key(self, command: BotCommand) -> str:
        """Unique key for tracking in-flight futures."""
        # Use the message ID for stability across reschedules
        msg_id = command.message.id if command.message else ""
        return f"{self.command()}:{command.source.id}:{msg_id}"

    def _status_channel(self, command: BotCommand) -> Channel:
        """Return the channel where status/progress messages should go.

        When /room redirect is used, status updates go to the origin channel
        (where the user typed the command) rather than the redirect destination.
        """
        if command.message and command.message.channel_id:
            origin_id = command.message.channel_id
            origin_name = command.message.channel.name if command.message.channel else ""
            if origin_id != command.channel_id:
                return Channel(id=origin_id, name=origin_name)
        return command.channel

    def _incoming_image_attachments(self, command: BotCommand) -> List[Any]:
        """Return image attachments on the incoming message, if any."""
        msg = command.message
        if not msg or not getattr(msg, "attachments", None):
            return []
        images = []
        for att in msg.attachments:
            content_type = getattr(att, "content_type", "") or ""
            att_type = getattr(getattr(att, "attachment_type", None), "value", "")
            if content_type.startswith("image/") or att_type == "image":
                images.append(att)
        return images

    def _build_model_prompt(self, command: BotCommand, prompt: str) -> Union[str, List[Any]]:
        """Assemble the prompt for the model, attaching incoming images.

        Downloads any image attachments on the incoming message (via the
        backend, on its event loop) and returns a list of pydantic-ai
        content parts so the model can see them. Falls back to the plain
        text prompt when there are no images or download is unavailable.
        """
        if not self.include_incoming_images:
            return prompt

        images = self._incoming_image_attachments(command)
        if not images:
            return prompt

        backend = self._backends.get(command.backend)
        if backend is None:
            return prompt

        from pydantic_ai import BinaryContent

        backend_loop = self._backend_loops.get(command.backend)
        parts: List[Any] = [prompt]
        for att in images:
            if getattr(att, "size", None) and att.size > self.max_incoming_image_bytes:
                log.warning("Skipping incoming image %r: %s bytes exceeds limit", getattr(att, "filename", ""), att.size)
                continue
            try:
                data = self._download_on_loop(backend, att, command.message, backend_loop)
            except Exception:
                log.exception("Failed to download incoming image %r", getattr(att, "filename", ""))
                continue
            if not data or len(data) > self.max_incoming_image_bytes:
                continue
            media_type = getattr(att, "content_type", "") or "image/png"
            parts.append(BinaryContent(data=data, media_type=media_type))

        # Only return a multimodal list if we actually attached an image.
        return parts if len(parts) > 1 else prompt

    @staticmethod
    def _download_on_loop(
        backend: BackendBase,
        attachment: Any,
        message: Optional[Message],
        loop: Optional[asyncio.AbstractEventLoop],
    ) -> bytes:
        """Download an attachment, reusing the backend's event loop if running."""
        coro = backend.download_attachment(attachment, message=message)
        if loop is not None and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    def preexecute(self, command: BotCommand) -> BotCommand:
        """Submit the LLM call to a thread pool and schedule a check."""
        removed_sessions = self._sessions.cleanup_expired()
        if removed_sessions:
            log.debug("Cleaned up %d expired agent sessions", removed_sessions)

        key = self._command_key(command)
        if key not in self._futures:
            try:
                agent = self.build_agent(command)
                prompt_text = self.build_prompt(command)
                prompt = self._build_model_prompt(command, prompt_text)
            except Exception:
                log.exception("Error building agent/prompt for %s", self.command())
                command.args = ("ERROR: Failed to initialize the AI agent.",)
                return command

            # Resolve session history
            session = self._get_session(command) or self._create_session(command)
            history = session.message_history or None

            # Use the backend's event loop so aiohttp sessions stay valid
            backend_loop = self._backend_loops.get(command.backend)
            future = _executor.submit(_run_agent, agent, prompt, backend_loop, history)
            self._futures[key] = future
            log.info(
                "AgentCommand[%s] submitted for user %s (session history: %d msgs)",
                self.command(),
                command.source.name,
                len(session.message_history),
            )

        command.delay = _utc_now() + timedelta(seconds=self.poll_interval)
        return command

    def execute(self, command: BotCommand) -> Optional[Union[Message, List[Union[Message, "BaseCommand"]], "BaseCommand"]]:
        """Return result when ready; reschedule if still running."""
        # Handle errors from preexecute
        if command.args and len(command.args) == 1 and str(command.args[0]).startswith("ERROR:"):
            return Message(
                content=str(command.args[0]),
                channel=command.channel,
                metadata={"backend": command.backend},
            )

        key = self._command_key(command)
        future = self._futures.get(key)

        if future is None:
            log.warning("AgentCommand[%s] no future found for key %s", self.command(), key)
            return Message(
                content="Sorry, something went wrong processing your request.",
                channel=command.channel,
                metadata={"backend": command.backend},
            )

        if not future.done():
            # Check timeout
            elapsed = command.times_run * self.poll_interval
            if elapsed >= self.timeout:
                self._futures.pop(key, None)
                future.cancel()
                return Message(
                    content="Sorry, the AI request timed out. Please try again.",
                    channel=command.channel,
                    metadata={"backend": command.backend},
                )
            # Reschedule — optionally with a status message
            command.delay = _utc_now() + timedelta(seconds=self.poll_interval)
            command.times_run += 1

            result: List[Any] = [command]
            if self.status_every_n_polls and self.status_messages:
                # Status messages go to the origin channel (where the user
                # typed the command), NOT the /room redirect destination.
                origin_channel = self._status_channel(command)
                if command.times_run == 1:
                    # First poll: always send initial status
                    status_text = self.status_messages[0]
                    result.append(
                        Message(
                            content=status_text,
                            channel=origin_channel,
                            metadata={"backend": command.backend},
                        )
                    )
                elif command.times_run % self.status_every_n_polls == 0:
                    idx = (command.times_run // self.status_every_n_polls) % len(self.status_messages)
                    status_text = self.status_messages[idx]
                    result.append(
                        Message(
                            content=status_text,
                            channel=origin_channel,
                            metadata={"backend": command.backend},
                        )
                    )
            return result

        # Future is done — get result
        self._futures.pop(key, None)
        try:
            result = future.result()
            output = str(result.output) if hasattr(result, "output") else str(result)

            # Persist conversation history in session
            session = self._get_session(command) or self._create_session(command)
            if hasattr(result, "all_messages"):
                session.message_history = list(result.all_messages())
            session.touch()

        except Exception:
            log.exception("AgentCommand[%s] agent execution failed", self.command())
            return Message(
                content="Sorry, there was an error processing your request.",
                channel=command.channel,
                metadata={"backend": command.backend},
            )

        # For Symphony, LLM output is markdown that must be converted to
        # MessageML.  Pre-wrapping here prevents the backend from treating
        # the content as pre-formatted MessageML.
        if command.backend == "symphony":
            messageml = convert_format(output, Format.MARKDOWN, Format.SYMPHONY_MESSAGEML)
            messageml = self.wrap_symphony_output(messageml, command)
            output = f"<messageML>{messageml}</messageML>"

        # Build response — include session key in metadata so the bot can
        # associate the response message ID back to the session later.
        response = Message(
            content=output,
            channel=command.channel,
            metadata={
                "backend": command.backend,
                "agent_session_key": self._session_key(command),
            },
        )
        return response

    def on_response_sent(self, session_key: str, response_message_id: str) -> None:
        """Associate a sent message ID with the session for reply tracking.

        Called by the Bot after the response message is published, so that
        future replies to that message can be routed back to this session.
        """
        self._sessions.update_response_id(session_key, response_message_id)
