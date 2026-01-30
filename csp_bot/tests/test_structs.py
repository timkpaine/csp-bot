"""Tests for csp-bot structs."""

from csp_bot.structs import BotMessage, CommandVariant


class TestBotMessage:
    """Tests for BotMessage struct."""

    def test_create_bot_message(self):
        """Test creating a BotMessage."""
        msg = BotMessage(
            content="Hello world",
            channel_id="C123",
            backend="slack",
        )
        assert msg.content == "Hello world"
        assert msg.channel_id == "C123"
        assert msg.backend == "slack"


class TestCommandVariant:
    """Tests for CommandVariant enum."""

    def test_command_variants(self):
        """Test CommandVariant enum values."""
        assert CommandVariant.NO_RESPONSE.value == 0
        assert CommandVariant.REPLY.value == 1
        assert CommandVariant.REPLY_TO_AUTHOR.value == 2
        assert CommandVariant.REPLY_TO_OTHER.value == 3
