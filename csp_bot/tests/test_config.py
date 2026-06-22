"""Tests for BotConfig and related configuration classes."""

from csp_bot import BotConfig
from csp_bot.bot_config import SlackConfig, SymphonyConfig, TelegramConfig


class TestBotConfig:
    """Tests for BotConfig class."""

    def test_empty_config(self):
        """Test creating a BotConfig with no backends."""
        config = BotConfig()
        assert config.discord is None
        assert config.slack is None
        assert config.symphony is None
        assert config.telegram is None

    def test_config_with_slack(self):
        """Test creating a BotConfig with Slack backend."""
        slack_config = SlackConfig(
            channels={"general", "random"},
        )
        config = BotConfig(slack=slack_config)
        assert config.slack is not None
        assert "general" in config.slack.channels

    def test_config_with_multiple_backends(self):
        """Test creating a BotConfig with several backends at once."""
        config = BotConfig(
            slack=SlackConfig(bot_name="Bot"),
            telegram=TelegramConfig(bot_name="Bot"),
        )
        assert config.slack is not None
        assert config.telegram is not None
        assert config.discord is None
        assert config.symphony is None


class TestBackendConfig:
    """Tests for backend configuration classes."""

    def test_slack_config_defaults(self):
        """Test SlackConfig default values."""
        config = SlackConfig()
        assert config.bot_name == ""  # Empty by default, auto-detected
        assert config.channels == set()

    def test_symphony_config_defaults(self):
        """Test SymphonyConfig default values."""
        config = SymphonyConfig()
        assert config.bot_name == ""  # Empty by default, auto-detected
        assert config.set_presence_seconds == 0

    def test_explicit_bot_name(self):
        """Test explicit bot_name override."""
        config = SlackConfig(bot_name="MyBot")
        assert config.bot_name == "MyBot"
