"""Tests for the Bot class."""

from chatom.base import Channel, User

from csp_bot import Bot, BotConfig, Message


class TestBotInit:
    """Tests for Bot initialization."""

    def test_create_bot(self, bot_config):
        """Test creating a Bot instance."""
        bot = Bot(config=bot_config)
        assert bot.config is not None

    def test_create_bot_empty_config(self):
        """Test creating a Bot with empty config."""
        config = BotConfig()
        bot = Bot(config=config)
        assert bot.config.slack is None
        assert bot.config.symphony is None


class TestMessageHandling:
    """Tests for message handling with chatom types."""

    def test_chatom_message_fields(self, sample_message):
        """Test that chatom Message has expected fields."""
        assert sample_message.content == "Hello world"
        assert sample_message.author_id == "U123"
        assert sample_message.channel_id == "C123"
        assert sample_message.backend == "slack"

    def test_create_message_with_mentions(self):
        """Test creating a message with mentions."""
        msg = Message(
            id="msg456",
            content="Hello <@U123> and <@U456>",
            author=User(id="U789"),
            channel=Channel(id="C123"),
            mentions=[User(id="U123"), User(id="U456")],
            backend="slack",
        )
        assert len(msg.mention_ids) == 2
        assert "U123" in msg.mention_ids
        assert "U456" in msg.mention_ids
