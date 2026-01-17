"""Tests for Message struct conversions between backends."""

import pytest

from csp_bot.structs import BotCommand, CommandVariant, Message, User

# Import raw message types (these may be stubs if adapters not installed)
try:
    from csp_adapter_symphony import SymphonyMessage

    SYMPHONY_AVAILABLE = True
except ImportError:
    from csp_bot.backends.symphony import SymphonyMessage

    SYMPHONY_AVAILABLE = False

try:
    from csp_adapter_slack import SlackMessage

    SLACK_AVAILABLE = True
except ImportError:
    from csp_bot.backends.slack import SlackMessage

    SLACK_AVAILABLE = False

try:
    from csp_adapter_discord import DiscordMessage

    DISCORD_AVAILABLE = True
except ImportError:
    from csp_bot.backends.discord import DiscordMessage

    DISCORD_AVAILABLE = False


class TestMessageFromRawSymphony:
    """Tests for Message.from_raw_message with Symphony messages."""

    @pytest.mark.skipif(not SYMPHONY_AVAILABLE, reason="Symphony adapter not installed")
    def test_from_symphony_room_message(self):
        """Test converting Symphony room message to Message."""
        raw = SymphonyMessage(
            user="John Doe",
            user_email="john@example.com",
            user_id="123456789",
            tags=["987654321", "111111111"],
            room="Test Room",
            msg="Hello <mention uid='987654321'>@Alice</mention>",
            form_id="",
            form_values={},
        )
        msg = Message.from_raw_message("symphony", raw)

        assert msg.user == "John Doe"
        assert msg.user_email == "john@example.com"
        assert msg.user_id == "123456789"
        assert msg.tags == ["987654321", "111111111"]
        assert msg.msg == "Hello <mention uid='987654321'>@Alice</mention>"
        assert msg.backend == "symphony"
        assert msg.channel == "Test Room"
        assert msg._raw == raw

    @pytest.mark.skipif(not SYMPHONY_AVAILABLE, reason="Symphony adapter not installed")
    def test_from_symphony_dm_message(self):
        """Test converting Symphony DM message - DM without room_id raises error."""
        raw = SymphonyMessage(
            user="John Doe",
            user_email="john@example.com",
            user_id="123456789",
            tags=[],
            room="DM",  # DM indicator
            msg="Hello!",
            form_id="",
            form_values={},
        )
        # SymphonyMessage struct doesn't have room_id field
        # This will raise AttributeError when trying to access msg.room_id
        # This is expected behavior - test documents current implementation
        with pytest.raises(AttributeError):
            Message.from_raw_message("symphony", raw)


class TestMessageFromRawSlack:
    """Tests for Message.from_raw_message with Slack messages."""

    @pytest.mark.skipif(not SLACK_AVAILABLE, reason="Slack adapter not installed")
    def test_from_slack_channel_message(self):
        """Test converting Slack channel message to Message."""
        raw = SlackMessage(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=["U987654321"],
            channel="general",
            channel_id="C123456789",
            channel_type="public",
            msg="<@U987654321> hello!",
            reaction="",
            thread="",
            payload={},
        )
        msg = Message.from_raw_message("slack", raw)

        assert msg.user == "alice"
        assert msg.user_email == "alice@example.com"
        assert msg.user_id == "U123456789"
        assert msg.tags == ["U987654321"]
        assert msg.msg == "<@U987654321> hello!"
        assert msg.backend == "slack"
        assert msg.channel == "general"
        assert msg.reaction == ""
        assert msg.thread == ""

    @pytest.mark.skipif(not SLACK_AVAILABLE, reason="Slack adapter not installed")
    def test_from_slack_dm_message(self):
        """Test converting Slack DM message to Message."""
        raw = SlackMessage(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=[],
            channel="DM",  # DM indicator
            channel_id="D123456789",
            channel_type="im",
            msg="Hello there!",
            reaction="",
            thread="",
            payload={},
        )
        msg = Message.from_raw_message("slack", raw)

        assert msg.backend == "slack"
        # DM channels should use channel_id
        assert msg.channel == "D123456789"

    @pytest.mark.skipif(not SLACK_AVAILABLE, reason="Slack adapter not installed")
    def test_from_slack_threaded_message(self):
        """Test converting Slack threaded message to Message."""
        raw = SlackMessage(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=[],
            channel="general",
            channel_id="C123456789",
            channel_type="public",
            msg="Reply in thread",
            reaction="",
            thread="1234567890.123456",
            payload={},
        )
        msg = Message.from_raw_message("slack", raw)

        assert msg.thread == "1234567890.123456"

    @pytest.mark.skipif(not SLACK_AVAILABLE, reason="Slack adapter not installed")
    def test_from_slack_reaction_message(self):
        """Test converting Slack reaction to Message."""
        raw = SlackMessage(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=[],
            channel="general",
            channel_id="C123456789",
            channel_type="public",
            msg="",
            reaction="thumbsup",
            thread="1234567890.123456",
            payload={},
        )
        msg = Message.from_raw_message("slack", raw)

        assert msg.reaction == "thumbsup"
        assert msg.thread == "1234567890.123456"


class TestMessageFromRawDiscord:
    """Tests for Message.from_raw_message with Discord messages."""

    @pytest.mark.skipif(not DISCORD_AVAILABLE, reason="Discord adapter not installed")
    def test_from_discord_channel_message(self):
        """Test converting Discord channel message to Message."""
        raw = DiscordMessage(
            user="bob",
            user_email="bob@example.com",
            user_id="123456789012345678",
            tags=["987654321098765432"],
            channel="general",
            channel_id="111222333444555666",
            channel_type="public",
            msg="<@987654321098765432> hello!",
            reaction="",
            thread="",
            payload=None,
        )
        msg = Message.from_raw_message("discord", raw)

        assert msg.user == "bob"
        assert msg.user_email == "bob@example.com"
        assert msg.user_id == "123456789012345678"
        assert msg.tags == ["987654321098765432"]
        assert msg.msg == "<@987654321098765432> hello!"
        assert msg.backend == "discord"
        assert msg.channel == "general"

    @pytest.mark.skipif(not DISCORD_AVAILABLE, reason="Discord adapter not installed")
    def test_from_discord_dm_message(self):
        """Test converting Discord DM message to Message."""
        raw = DiscordMessage(
            user="bob",
            user_email="bob@example.com",
            user_id="123456789012345678",
            tags=[],
            channel="DM",
            channel_id="999888777666555444",
            channel_type="message",
            msg="Private hello!",
            reaction="",
            thread="",
            payload=None,
        )
        msg = Message.from_raw_message("discord", raw)

        assert msg.backend == "discord"
        assert msg.channel == "999888777666555444"


class TestMessageToRawSymphony:
    """Tests for Message.to_raw_message for Symphony."""

    def test_to_symphony_message(self):
        """Test converting Message to Symphony raw message."""
        msg = Message(
            user="John Doe",
            user_email="john@example.com",
            user_id="123456789",
            tags=["987654321"],
            msg="Hello world!",
            channel="Test Room",
            backend="symphony",
            reaction="",
            thread="",
        )
        raw = msg.to_raw_message("symphony")

        assert raw.user == "John Doe"
        assert raw.user_email == "john@example.com"
        assert raw.user_id == "123456789"
        assert raw.tags == ["987654321"]
        assert raw.msg == "Hello world!"
        assert raw.room == "Test Room"


class TestMessageToRawSlack:
    """Tests for Message.to_raw_message for Slack."""

    def test_to_slack_message(self):
        """Test converting Message to Slack raw message."""
        msg = Message(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=["U987654321"],
            msg="Hello <@U987654321>!",
            channel="general",
            backend="slack",
            reaction="",
            thread="",
        )
        raw = msg.to_raw_message("slack")

        assert raw.user == "alice"
        assert raw.user_email == "alice@example.com"
        assert raw.user_id == "U123456789"
        assert raw.tags == ["U987654321"]
        assert raw.msg == "Hello <@U987654321>!"
        assert raw.channel == "general"

    def test_to_slack_reaction(self):
        """Test converting Message with reaction to Slack raw message."""
        msg = Message(
            user="alice",
            user_email="alice@example.com",
            user_id="U123456789",
            tags=[],
            msg="",
            channel="general",
            backend="slack",
            reaction="thumbsup",
            thread="1234567890.123456",
        )
        raw = msg.to_raw_message("slack")

        assert raw.reaction == "thumbsup"
        assert raw.thread == "1234567890.123456"


class TestMessageToRawDiscord:
    """Tests for Message.to_raw_message for Discord."""

    def test_to_discord_message(self):
        """Test converting Message to Discord raw message."""
        msg = Message(
            user="bob",
            user_email="bob@example.com",
            user_id="123456789012345678",
            tags=["987654321098765432"],
            msg="Hello <@987654321098765432>!",
            channel="general",
            backend="discord",
            reaction="",
            thread="",
        )
        raw = msg.to_raw_message("discord")

        assert raw.user == "bob"
        assert raw.user_email == "bob@example.com"
        assert raw.user_id == "123456789012345678"
        assert raw.tags == ["987654321098765432"]
        assert raw.msg == "Hello <@987654321098765432>!"
        assert raw.channel == "general"


class TestMessageUnsupportedBackend:
    """Tests for unsupported backend handling."""

    def test_from_raw_unsupported_backend(self):
        """Test that unsupported backend raises NotImplementedError."""

        # Create a mock raw message
        class FakeMessage:
            pass

        with pytest.raises(NotImplementedError, match="not supported"):
            Message.from_raw_message("irc", FakeMessage())

    def test_to_raw_unsupported_backend(self):
        """Test that unsupported backend raises NotImplementedError."""
        msg = Message(
            user="user",
            user_email="",
            user_id="123",
            tags=[],
            msg="test",
            channel="test",
            backend="irc",
            reaction="",
            thread="",
        )
        with pytest.raises(NotImplementedError, match="not supported"):
            msg.to_raw_message("irc")


class TestBotCommand:
    """Tests for BotCommand struct."""

    def test_bot_command_creation(self):
        """Test creating a BotCommand."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/help",
            channel="general",
            tags=[],
            backend="slack",
        )
        cmd = BotCommand(
            command="help",
            args=tuple(),
            source=User(name="alice", id="U123", backend="slack"),
            targets=tuple(),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=msg,
        )

        assert cmd.command == "help"
        assert cmd.args == tuple()
        assert cmd.source.name == "alice"
        assert cmd.channel == "general"
        assert cmd.variant == CommandVariant.REPLY

    def test_bot_command_with_targets(self):
        """Test BotCommand with target users."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/thanks <@U456>",
            channel="general",
            tags=["U456"],
            backend="slack",
        )
        cmd = BotCommand(
            command="thanks",
            args=tuple(),
            source=User(name="alice", id="U123", backend="slack"),
            targets=(User(name="bob", id="U456", backend="slack"),),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY_TO_OTHER,
            message=msg,
        )

        assert len(cmd.targets) == 1
        assert cmd.targets[0].name == "bob"
        assert cmd.variant == CommandVariant.REPLY_TO_OTHER


class TestCommandVariant:
    """Tests for CommandVariant enum."""

    def test_command_variants(self):
        """Test all command variant values."""
        assert CommandVariant.NO_RESPONSE.value == 0
        assert CommandVariant.REPLY.value == 1
        assert CommandVariant.REPLY_TO_AUTHOR.value == 2
        assert CommandVariant.REPLY_TO_OTHER.value == 3
        assert CommandVariant.REPLY_TO_ALL.value == 4


class TestUser:
    """Tests for User struct."""

    def test_user_creation(self):
        """Test creating a User."""
        user = User(name="alice", id="U123", backend="slack")

        assert user.name == "alice"
        assert user.id == "U123"
        assert user.backend == "slack"

    def test_user_different_backends(self):
        """Test User for different backends."""
        slack_user = User(name="alice", id="U123456789", backend="slack")
        discord_user = User(name="bob", id="123456789012345678", backend="discord")
        symphony_user = User(name="John Doe", id="123456789", backend="symphony")

        assert slack_user.backend == "slack"
        assert discord_user.backend == "discord"
        assert symphony_user.backend == "symphony"
