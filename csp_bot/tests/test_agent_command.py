"""Tests for AgentCommand base class."""

import asyncio
import threading
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from chatom import Message, User
from chatom.backend import BackendBase

from csp_bot.commands.agent import AgentCommand, AgentSession, SessionStore, _run_agent
from csp_bot.structs import BotCommand, CommandVariant


class ConcreteAgentCommand(AgentCommand):
    """Minimal concrete subclass for testing."""

    def command(self):
        return "test-agent"

    def name(self):
        return "Test Agent"

    def help(self):
        return "/test-agent — a test agent command"

    def build_agent(self, command):
        from pydantic_ai import Agent

        return Agent("test", system_prompt="You are a test agent.")

    def build_prompt(self, command):
        return " ".join(command.args) if command.args else "Hello"


@pytest.fixture
def cmd():
    """Fresh AgentCommand instance with clean state."""
    AgentCommand._futures = {}
    AgentCommand._backends = {}
    AgentCommand._sessions = SessionStore(ttl_seconds=900.0)
    return ConcreteAgentCommand()


@pytest.fixture
def bot_command():
    """Create a BotCommand for testing."""
    return BotCommand(
        command="test-agent",
        args=("summarize", "this"),
        source=User(id="U123", name="Test User"),
        targets=(),
        channel_id="C456",
        channel_name="general",
        backend="slack",
        variant=CommandVariant.REPLY,
        message=Message(id="msg1", content="/test-agent summarize this"),
        delay=datetime.now(timezone.utc),
        schedule="",
        times_run=0,
    )


@pytest.fixture
def mock_backend():
    """Create a mock BackendBase."""
    backend = MagicMock(spec=BackendBase)
    backend.name = "slack"
    backend.capabilities = MagicMock()
    backend.capabilities.supports = MagicMock(return_value=True)
    return backend


class TestSetBackends:
    def test_set_backends(self, mock_backend):
        AgentCommand.set_backends({"slack": mock_backend})
        assert AgentCommand._backends == {"slack": mock_backend}
        # Cleanup
        AgentCommand._backends = {}

    def test_build_toolset_returns_toolset_when_backend_available(self, cmd, bot_command, mock_backend):
        AgentCommand.set_backends({"slack": mock_backend})
        toolset = cmd.build_toolset(bot_command)
        assert toolset is not None
        AgentCommand._backends = {}

    def test_build_toolset_returns_none_when_no_backend(self, cmd, bot_command):
        AgentCommand.set_backends({})
        toolset = cmd.build_toolset(bot_command)
        assert toolset is None


class TestPreexecute:
    def test_submits_future_and_sets_delay(self, cmd, bot_command):
        with patch("csp_bot.commands.agent._executor") as mock_executor:
            mock_future = MagicMock(spec=Future)
            mock_executor.submit.return_value = mock_future

            result = cmd.preexecute(bot_command)

            assert mock_executor.submit.called
            assert result.delay.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(seconds=5)
            # Future should be stored
            assert len(AgentCommand._futures) == 1

    def test_does_not_resubmit_existing_future(self, cmd, bot_command):
        with patch("csp_bot.commands.agent._executor") as mock_executor:
            mock_future = MagicMock(spec=Future)
            mock_executor.submit.return_value = mock_future

            cmd.preexecute(bot_command)
            cmd.preexecute(bot_command)

            # Should only submit once
            assert mock_executor.submit.call_count == 1

    def test_handles_build_agent_error(self, cmd, bot_command):
        with patch.object(cmd, "build_agent", side_effect=RuntimeError("fail")):
            result = cmd.preexecute(bot_command)
            assert result.args[0].startswith("ERROR:")

    def test_cleans_up_expired_sessions(self, cmd, bot_command):
        AgentCommand._sessions = SessionStore(ttl_seconds=0.01)
        expired = AgentSession(user_id="U1", channel_id="C1", command_name="ask", bot_response_id="old-response")
        expired.last_active = datetime.now(timezone.utc) - timedelta(seconds=1)
        AgentCommand._sessions.put("old-key", expired)

        with patch("csp_bot.commands.agent._executor") as mock_executor:
            mock_executor.submit.return_value = MagicMock(spec=Future)
            cmd.preexecute(bot_command)

        assert AgentCommand._sessions.get("old-key") is None
        assert AgentCommand._sessions.get_by_response_id("old-response") is None


class TestExecute:
    def test_returns_error_message_from_preexecute(self, cmd, bot_command):
        bot_command.args = ("ERROR: Failed to initialize",)
        result = cmd.execute(bot_command)
        assert isinstance(result, Message)
        assert "ERROR:" in result.content

    def test_reschedules_when_future_not_done(self, cmd, bot_command):
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = False
        AgentCommand._futures[key] = mock_future

        result = cmd.execute(bot_command)
        # Should return a list with the rescheduled command and a status message
        assert isinstance(result, list)
        commands = [r for r in result if isinstance(r, BotCommand)]
        messages = [r for r in result if isinstance(r, Message)]
        assert len(commands) == 1
        assert commands[0].times_run == 1
        # First poll sends initial "Thinking..." status
        assert len(messages) == 1
        assert "Thinking" in messages[0].content

    def test_returns_result_when_future_done(self, cmd, bot_command):
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = True
        mock_result = MagicMock()
        mock_result.output = "Here is your summary."
        mock_result.all_messages.return_value = [{"role": "user", "content": "test"}]
        mock_future.result.return_value = mock_result
        AgentCommand._futures[key] = mock_future

        result = cmd.execute(bot_command)
        assert isinstance(result, Message)
        assert result.content == "Here is your summary."
        assert key not in AgentCommand._futures

    def test_handles_future_exception(self, cmd, bot_command):
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = True
        mock_future.result.side_effect = RuntimeError("LLM failed")
        AgentCommand._futures[key] = mock_future

        result = cmd.execute(bot_command)
        assert isinstance(result, Message)
        assert "error" in result.content.lower()
        assert key not in AgentCommand._futures

    def test_timeout_cancels_future(self, cmd, bot_command):
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = False
        AgentCommand._futures[key] = mock_future

        # Simulate many poll cycles exceeding timeout
        bot_command.times_run = cmd.timeout // cmd.poll_interval + 1
        result = cmd.execute(bot_command)

        assert isinstance(result, Message)
        assert "timed out" in result.content.lower()
        mock_future.cancel.assert_called_once()
        assert key not in AgentCommand._futures

    def test_no_future_returns_error(self, cmd, bot_command):
        bot_command.args = ()  # Clear any error args
        result = cmd.execute(bot_command)
        assert isinstance(result, Message)
        assert "something went wrong" in result.content.lower()


class TestRunAgent:
    def test_uses_threadsafe_submission_for_running_backend_loop(self):
        class FakeAgent:
            async def run(self, prompt, message_history=None):
                await asyncio.sleep(0)
                return {"prompt": prompt, "message_history": message_history}

        loop = asyncio.new_event_loop()
        loop_ready = threading.Event()

        def run_loop():
            asyncio.set_event_loop(loop)
            loop_ready.set()
            loop.run_forever()

        loop_thread = threading.Thread(target=run_loop, daemon=True)
        loop_thread.start()
        loop_ready.wait(timeout=1)

        try:
            result = _run_agent(FakeAgent(), "hello", loop, ["previous"])
        finally:
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=1)
            loop.close()

        assert result == {"prompt": "hello", "message_history": ["previous"]}


class TestSessionStore:
    def test_put_and_get(self):
        store = SessionStore(ttl_seconds=60.0)
        session = AgentSession(user_id="U1", channel_id="C1", command_name="ask")
        store.put("key1", session)
        assert store.get("key1") is session

    def test_get_returns_none_for_missing_key(self):
        store = SessionStore(ttl_seconds=60.0)
        assert store.get("nonexistent") is None

    def test_expired_session_returns_none(self):
        store = SessionStore(ttl_seconds=0.01)
        session = AgentSession(user_id="U1", channel_id="C1", command_name="ask")
        session.last_active = datetime.now(timezone.utc) - timedelta(seconds=1)
        store.put("key1", session)
        assert store.get("key1") is None

    def test_get_by_response_id(self):
        store = SessionStore(ttl_seconds=60.0)
        session = AgentSession(user_id="U1", channel_id="C1", command_name="ask", bot_response_id="resp1")
        store.put("key1", session)
        assert store.get_by_response_id("resp1") is session

    def test_get_by_response_id_returns_none_for_unknown(self):
        store = SessionStore(ttl_seconds=60.0)
        assert store.get_by_response_id("unknown") is None

    def test_update_response_id(self):
        store = SessionStore(ttl_seconds=60.0)
        session = AgentSession(user_id="U1", channel_id="C1", command_name="ask")
        store.put("key1", session)
        store.update_response_id("key1", "new-resp-id")
        assert store.get_by_response_id("new-resp-id") is session

    def test_update_response_id_removes_old_mapping(self):
        store = SessionStore(ttl_seconds=60.0)
        session = AgentSession(user_id="U1", channel_id="C1", command_name="ask", bot_response_id="old-id")
        store.put("key1", session)
        store.update_response_id("key1", "new-id")
        assert store.get_by_response_id("old-id") is None
        assert store.get_by_response_id("new-id") is session

    def test_cleanup_expired(self):
        store = SessionStore(ttl_seconds=0.01)
        s1 = AgentSession(user_id="U1", channel_id="C1", command_name="ask")
        s1.last_active = datetime.now(timezone.utc) - timedelta(seconds=1)
        s2 = AgentSession(user_id="U2", channel_id="C2", command_name="ask")
        store.put("key1", s1)
        store.put("key2", s2)
        removed = store.cleanup_expired()
        assert removed == 1
        assert store.get("key1") is None
        assert store.get("key2") is s2

    def test_cleanup_expired_removes_response_index(self):
        store = SessionStore(ttl_seconds=0.01)
        expired = AgentSession(user_id="U1", channel_id="C1", command_name="ask", bot_response_id="old-response")
        expired.last_active = datetime.now(timezone.utc) - timedelta(seconds=1)
        active = AgentSession(user_id="U2", channel_id="C2", command_name="ask", bot_response_id="new-response")
        store.put("old-key", expired)
        store.put("new-key", active)

        removed = store.cleanup_expired()

        assert removed == 1
        assert store.get_by_response_id("old-response") is None
        assert store.get_by_response_id("new-response") is active


def _sample_history():
    """Build a small but real pydantic-ai message history."""
    from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

    return [
        ModelRequest(parts=[UserPromptPart(content="What is 2+2?")]),
        ModelResponse(parts=[TextPart(content="4")]),
    ]


class TestAgentSessionSerialization:
    """Round-trip tests for the AgentSession serialization schema."""

    def test_to_dict_is_json_safe(self):
        import json

        session = AgentSession(
            user_id="U1",
            channel_id="C1",
            command_name="ask",
            message_history=_sample_history(),
            bot_response_id="resp1",
        )
        data = session.to_dict()
        # Must be serializable to JSON without custom encoders.
        json.dumps(data)
        assert data["schema_version"] == AgentSession.SCHEMA_VERSION
        assert data["user_id"] == "U1"
        assert data["bot_response_id"] == "resp1"

    def test_round_trip_preserves_fields(self):
        original = AgentSession(
            user_id="U1",
            channel_id="C1",
            command_name="ask",
            message_history=_sample_history(),
            bot_response_id="resp1",
        )
        restored = AgentSession.from_dict(original.to_dict())
        assert restored.user_id == original.user_id
        assert restored.channel_id == original.channel_id
        assert restored.command_name == original.command_name
        assert restored.bot_response_id == original.bot_response_id
        assert len(restored.message_history) == len(original.message_history)
        # The reconstructed history must round-trip identically.
        assert restored.to_dict()["message_history"] == original.to_dict()["message_history"]

    def test_round_trip_through_json_string(self):
        import json

        original = AgentSession(
            user_id="U1",
            channel_id="C1",
            command_name="ask",
            message_history=_sample_history(),
        )
        restored = AgentSession.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored.command_name == "ask"
        assert len(restored.message_history) == 2

    def test_from_dict_rejects_unknown_schema_version(self):
        data = AgentSession(user_id="U1", channel_id="C1", command_name="ask").to_dict()
        data["schema_version"] = 999
        with pytest.raises(ValueError, match="schema version"):
            AgentSession.from_dict(data)


class TestSessionStorePersistence:
    """Sessions backed by a StateStore, including a durable backend."""

    def test_store_accepts_serialized_dict_values(self):
        """A JSON-style store that holds dicts is transparently reconstructed."""
        from csp_bot.persistence import InMemoryStateStore

        backend = InMemoryStateStore()
        store = SessionStore(ttl_seconds=900.0, store=backend)
        session = AgentSession(
            user_id="U1",
            channel_id="C1",
            command_name="ask",
            message_history=_sample_history(),
            bot_response_id="resp1",
        )
        # Simulate a durable backend that persists the serialized form.
        backend.put(SessionStore.namespace, session.store_key, session.to_dict())
        backend.put(SessionStore.response_namespace, "resp1", session.store_key)

        loaded = store.get(session.store_key)
        assert loaded is not None
        assert loaded.user_id == "U1"
        assert len(loaded.message_history) == 2
        assert store.get_by_response_id("resp1").store_key == session.store_key

    def test_survives_store_handoff(self):
        """A fresh SessionStore over the same backend sees prior sessions."""
        from csp_bot.persistence import FsspecStateStore

        backend = FsspecStateStore("memory://agent-sessions-test")
        backend.clear()
        store = SessionStore(ttl_seconds=900.0, store=backend)
        session = AgentSession(
            user_id="U1",
            channel_id="C1",
            command_name="ask",
            message_history=_sample_history(),
        )
        store.put(session.store_key, session)
        store.update_response_id(session.store_key, "bot-msg-1")

        # Simulate a restart: brand-new SessionStore over the same storage.
        reopened = SessionStore(ttl_seconds=900.0, store=backend)
        resumed = reopened.get_by_response_id("bot-msg-1")
        assert resumed is not None
        assert resumed.command_name == "ask"
        assert len(resumed.message_history) == 2
        backend.clear()


class TestSessionStoreInjection:
    """AgentCommand.set_session_store wiring."""

    def test_set_session_store_swaps_backend(self):
        from csp_bot.persistence import InMemoryStateStore

        backend = InMemoryStateStore()
        AgentCommand.set_session_store(backend, ttl_seconds=123.0)
        try:
            assert AgentCommand._sessions.store is backend
            assert AgentCommand._sessions._ttl == 123.0
        finally:
            AgentCommand._sessions = SessionStore(ttl_seconds=900.0)

    def test_set_session_ttl_preserves_store(self):
        from csp_bot.persistence import InMemoryStateStore

        backend = InMemoryStateStore()
        AgentCommand.set_session_store(backend)
        try:
            AgentCommand.set_session_ttl(42.0)
            assert AgentCommand._sessions.store is backend
            assert AgentCommand._sessions._ttl == 42.0
        finally:
            AgentCommand._sessions = SessionStore(ttl_seconds=900.0)


class TestSessionIntegration:
    """Test session creation and resumption through AgentCommand."""

    def test_preexecute_creates_session(self, cmd, bot_command):
        with patch("csp_bot.commands.agent._executor") as mock_executor:
            mock_executor.submit.return_value = MagicMock(spec=Future)
            cmd.preexecute(bot_command)

        key = cmd._session_key(bot_command)
        session = AgentCommand._sessions.get(key)
        assert session is not None
        assert session.user_id == "U123"
        assert session.channel_id == "C456"
        assert session.command_name == "test-agent"

    def test_execute_stores_message_history(self, cmd, bot_command):
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = True
        mock_result = MagicMock()
        mock_result.output = "Some answer"
        mock_history = [MagicMock(), MagicMock()]
        mock_result.all_messages.return_value = mock_history
        AgentCommand._futures[key] = mock_future
        mock_future.result.return_value = mock_result

        # Pre-create session as preexecute would
        cmd._create_session(bot_command)

        result = cmd.execute(bot_command)
        assert isinstance(result, Message)

        session = AgentCommand._sessions.get(cmd._session_key(bot_command))
        assert session is not None
        assert session.message_history == mock_history

    def test_session_resumed_on_reply(self, cmd, bot_command):
        """Simulate a reply to a bot message resuming an existing session."""
        from chatom.base.message import MessageReference

        # First: create a session and register a response ID
        session = cmd._create_session(bot_command)
        session.message_history = [MagicMock(), MagicMock()]
        AgentCommand._sessions.update_response_id(cmd._session_key(bot_command), "bot-msg-123")

        # Second: create a reply message referencing the bot response
        reply_msg = Message(
            id="msg2",
            content="Tell me more",
            author=User(id="U123", name="Test User"),
            reference=MessageReference(message_id="bot-msg-123"),
        )
        reply_command = BotCommand(
            command="test-agent",
            args=("Tell me more",),
            source=User(id="U123", name="Test User"),
            targets=(),
            channel_id="C456",
            channel_name="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=reply_msg,
            delay=datetime.now(timezone.utc),
            schedule="",
            times_run=0,
        )

        # The session should be found via the reference
        found = cmd._get_session(reply_command)
        assert found is session
        assert len(found.message_history) == 2

    def test_session_key_format(self, cmd, bot_command):
        key = cmd._session_key(bot_command)
        assert key == "test-agent:U123:C456"

    def test_response_metadata_includes_session_key(self, cmd, bot_command):
        """Execute should include agent_session_key in response metadata."""
        key = cmd._command_key(bot_command)
        mock_future = MagicMock(spec=Future)
        mock_future.done.return_value = True
        mock_result = MagicMock()
        mock_result.output = "Answer"
        mock_result.all_messages.return_value = []
        mock_future.result.return_value = mock_result
        AgentCommand._futures[key] = mock_future

        cmd._create_session(bot_command)
        result = cmd.execute(bot_command)

        assert isinstance(result, Message)
        assert result.metadata["agent_session_key"] == "test-agent:U123:C456"


class TestMultimodalPrompt:
    """Incoming image attachments are passed to the model as multimodal input."""

    @staticmethod
    def _image_command(backend_name="slack"):
        from chatom.base import Image

        msg = Message(
            id="msg-img",
            content="/test-agent what is this",
            author=User(id="U123", name="Test User"),
            attachments=[Image(id="att1", filename="pic.png", content_type="image/png")],
        )
        return BotCommand(
            command="test-agent",
            args=("what", "is", "this"),
            source=User(id="U123", name="Test User"),
            targets=(),
            channel_id="C456",
            channel_name="general",
            backend=backend_name,
            variant=CommandVariant.REPLY,
            message=msg,
            delay=datetime.now(timezone.utc),
            schedule="",
            times_run=0,
        )

    def test_incoming_image_becomes_binary_content(self, cmd):
        from unittest.mock import AsyncMock

        from pydantic_ai import BinaryContent

        backend = MagicMock(spec=BackendBase)
        backend.download_attachment = AsyncMock(return_value=b"PNGBYTES")
        AgentCommand.set_backends({"slack": backend})
        try:
            command = self._image_command()
            parts = cmd._build_model_prompt(command, "what is this")
        finally:
            AgentCommand._backends = {}
            AgentCommand._backend_loops = {}

        assert isinstance(parts, list)
        assert parts[0] == "what is this"
        binaries = [p for p in parts if isinstance(p, BinaryContent)]
        assert len(binaries) == 1
        assert binaries[0].data == b"PNGBYTES"
        assert binaries[0].media_type == "image/png"
        backend.download_attachment.assert_awaited_once()

    def test_no_images_returns_plain_prompt(self, cmd, bot_command):
        backend = MagicMock(spec=BackendBase)
        AgentCommand.set_backends({"slack": backend})
        try:
            # bot_command has no attachments
            result = cmd._build_model_prompt(bot_command, "plain prompt")
        finally:
            AgentCommand._backends = {}

        assert result == "plain prompt"

    def test_disabled_flag_returns_plain_prompt(self, cmd):
        from unittest.mock import AsyncMock

        backend = MagicMock(spec=BackendBase)
        backend.download_attachment = AsyncMock(return_value=b"x")
        AgentCommand.set_backends({"slack": backend})
        cmd.include_incoming_images = False
        try:
            command = self._image_command()
            result = cmd._build_model_prompt(command, "prompt text")
        finally:
            AgentCommand._backends = {}
            cmd.include_incoming_images = True

        assert result == "prompt text"
        backend.download_attachment.assert_not_called()

    def test_download_failure_falls_back_to_text(self, cmd):
        from unittest.mock import AsyncMock

        backend = MagicMock(spec=BackendBase)
        backend.download_attachment = AsyncMock(side_effect=RuntimeError("boom"))
        AgentCommand.set_backends({"slack": backend})
        try:
            command = self._image_command()
            result = cmd._build_model_prompt(command, "prompt text")
        finally:
            AgentCommand._backends = {}

        # No image could be attached → fall back to the plain text prompt.
        assert result == "prompt text"

    def test_download_runs_on_provided_idle_loop(self):
        """The download must run on the backend's own (idle) loop, not a fresh
        one — the backend's aiohttp session is bound to that loop."""
        import asyncio

        loop = asyncio.new_event_loop()
        seen = {}

        class _Backend:
            async def download_attachment(self, attachment, message=None):
                seen["loop"] = asyncio.get_running_loop()
                return b"IMGDATA"

        try:
            result = AgentCommand._download_on_loop(_Backend(), object(), None, loop)
        finally:
            loop.close()

        assert result == b"IMGDATA"
        assert seen["loop"] is loop


class TestChannelContextNote:
    """The agent must be told which channel it is running in."""

    def test_note_includes_channel_id_and_name(self, cmd, bot_command):
        note = cmd._channel_context_note(bot_command)
        assert 'id="C456"' in note
        assert "general" in note
        assert "read_channel_history" in note

    def test_note_prefers_origin_message_channel(self, cmd):
        from chatom import Channel

        command = BotCommand(
            command="test-agent",
            args=(),
            source=User(id="U1", name="U"),
            targets=(),
            channel_id="REDIRECT",
            channel_name="redirect",
            backend="symphony",
            variant=CommandVariant.REPLY,
            message=Message(id="m", content="hi", channel=Channel(id="ORIGIN", name="the-room")),
            delay=datetime.now(timezone.utc),
            schedule="",
            times_run=0,
        )
        note = cmd._channel_context_note(command)
        assert 'id="ORIGIN"' in note
        assert "the-room" in note

    def test_note_empty_without_channel(self, cmd):
        command = BotCommand(
            command="test-agent",
            args=(),
            source=User(id="U1", name="U"),
            targets=(),
            channel_id="",
            channel_name="",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(id="m", content="hi"),
            delay=datetime.now(timezone.utc),
            schedule="",
            times_run=0,
        )
        assert cmd._channel_context_note(command) == ""


class TestPromptPrefix:
    """Root prompt and channel injection are configurable."""

    def test_default_prefix_is_channel_note(self, cmd, bot_command):
        prefix = cmd._prompt_prefix(bot_command)
        assert 'id="C456"' in prefix

    def test_inject_channel_false_omits_note(self, cmd, bot_command):
        cmd.inject_channel = False
        assert cmd._prompt_prefix(bot_command) == ""

    def test_root_prompt_prepended(self, cmd, bot_command):
        cmd.root_prompt = "ROOT RULES"
        prefix = cmd._prompt_prefix(bot_command)
        assert prefix.startswith("ROOT RULES")
        assert 'id="C456"' in prefix

    def test_root_prompt_only_when_channel_disabled(self, cmd, bot_command):
        cmd.inject_channel = False
        cmd.root_prompt = "ROOT RULES"
        assert cmd._prompt_prefix(bot_command) == "ROOT RULES"

    def test_build_root_prompt_override(self, bot_command):
        class CustomRoot(ConcreteAgentCommand):
            def build_root_prompt(self, command):
                return f"dynamic:{command.backend}"

        prefix = CustomRoot()._prompt_prefix(bot_command)
        assert "dynamic:slack" in prefix
