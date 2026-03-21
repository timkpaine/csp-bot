"""Tests for csp-bot structs."""

from chatom import Channel, Message, User

from csp_bot.structs import BotCommand, BotMessage, CommandVariant


class TestBotMessage:
    """Tests for BotMessage struct."""

    def test_create_bot_message(self):
        """Test creating a BotMessage."""
        msg = BotMessage(
            content="Hello world",
            channel_id="C123",
            channel_name="general",
            thread_id="",
            backend="slack",
            mentions=(),
            formatted=None,
            reply_to_id="",
        )
        assert msg.content == "Hello world"
        assert msg.channel_id == "C123"
        assert msg.backend == "slack"

    def test_bot_message_from_chatom_message(self):
        """Test creating BotMessage from a chatom Message."""
        chatom_msg = Message(
            id="msg123",
            content="Hello from chatom",
            author=User(id="U123", name="Test User"),
            channel=Channel(id="C456", name="test-channel"),
            mentions=[User(id="U789")],
        )

        bot_msg = BotMessage.from_chatom_message(chatom_msg, "slack")

        assert bot_msg.content == "Hello from chatom"
        assert bot_msg.channel_id == "C456"
        assert bot_msg.channel_name == "test-channel"
        assert bot_msg.backend == "slack"
        assert "U789" in bot_msg.mentions

    def test_bot_message_from_chatom_message_minimal(self):
        """Test creating BotMessage from minimal chatom Message."""
        chatom_msg = Message(content="Minimal message")

        bot_msg = BotMessage.from_chatom_message(chatom_msg, "symphony")

        assert bot_msg.content == "Minimal message"
        assert bot_msg.channel_id == ""
        assert bot_msg.channel_name == ""
        assert bot_msg.backend == "symphony"
        assert bot_msg.mentions == ()

    def test_bot_message_to_chatom_message(self):
        """Test converting BotMessage back to chatom Message."""
        bot_msg = BotMessage(
            content="Hello world",
            channel_id="C123",
            channel_name="general",
            thread_id="",  # Not directly supported in chatom Message
            backend="slack",
            mentions=("U789", "U012"),
            formatted=None,
            reply_to_id="",
        )

        chatom_msg = bot_msg.to_chatom_message()

        assert chatom_msg.content == "Hello world"
        assert chatom_msg.channel_id == "C123"
        assert chatom_msg.channel.name == "general"
        # Note: mention_ids may not be directly accessible - check what we have
        assert chatom_msg.channel is not None


class TestBotCommand:
    """Tests for BotCommand struct."""

    def test_channel_property(self):
        """Test BotCommand.channel returns a Channel object."""
        cmd = BotCommand(
            command="test",
            args=(),
            source=User(id="U123"),
            targets=(),
            channel_id="C456",
            channel_name="test-channel",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(content="test"),
            delay=None,
            schedule="",
            times_run=0,
        )

        channel = cmd.channel

        assert isinstance(channel, Channel)
        assert channel.id == "C456"
        assert channel.name == "test-channel"

    def test_original_message_property(self):
        """Test BotCommand.original_message returns the message."""
        original = Message(id="msg123", content="Original message")
        cmd = BotCommand(
            command="test",
            args=("arg1", "arg2"),
            source=User(id="U123"),
            targets=(),
            channel_id="C456",
            channel_name="test",
            backend="symphony",
            variant=CommandVariant.REPLY_TO_OTHER,
            message=original,
            delay=None,
            schedule="",
            times_run=0,
        )

        assert cmd.original_message is original
        assert cmd.original_message.content == "Original message"


class TestCommandVariant:
    """Tests for CommandVariant enum."""

    def test_command_variants(self):
        """Test CommandVariant enum values."""
        assert CommandVariant.NO_RESPONSE.value == 0
        assert CommandVariant.REPLY.value == 1
        assert CommandVariant.REPLY_TO_AUTHOR.value == 2
        assert CommandVariant.REPLY_TO_OTHER.value == 3

    def test_command_variant_reply_to_all(self):
        """Test REPLY_TO_ALL variant exists."""
        assert CommandVariant.REPLY_TO_ALL.value == 4
