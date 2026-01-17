"""Tests for backend module imports and fallbacks."""


class TestBackendImports:
    """Tests for backend module import behavior."""

    def test_discord_module_imports(self):
        """Test that discord module exports expected symbols."""
        from csp_bot.backends import discord

        # These should always be available
        assert hasattr(discord, "DiscordAdapterConfig")
        assert hasattr(discord, "DiscordAdapterManager")
        assert hasattr(discord, "DiscordMessage")
        assert hasattr(discord, "mention_user_discord")

        # Check __all__ exports
        assert "DiscordAdapterConfig" in discord.__all__
        assert "DiscordAdapterManager" in discord.__all__
        assert "DiscordMessage" in discord.__all__
        assert "mention_user_discord" in discord.__all__

    def test_slack_module_imports(self):
        """Test that slack module exports expected symbols."""
        from csp_bot.backends import slack

        # These should always be available
        assert hasattr(slack, "SlackAdapterConfig")
        assert hasattr(slack, "SlackAdapterManager")
        assert hasattr(slack, "SlackMessage")
        assert hasattr(slack, "mention_user_slack")

        # Check __all__ exports
        assert "SlackAdapterConfig" in slack.__all__
        assert "SlackAdapterManager" in slack.__all__
        assert "SlackMessage" in slack.__all__
        assert "mention_user_slack" in slack.__all__

    def test_symphony_module_imports(self):
        """Test that symphony module exports expected symbols."""
        from csp_bot.backends import symphony

        # These should always be available
        assert hasattr(symphony, "SymphonyAdapterConfig")
        assert hasattr(symphony, "SymphonyAdapter")
        assert hasattr(symphony, "SymphonyMessage")
        assert hasattr(symphony, "Presence")
        assert hasattr(symphony, "mention_user_symphony")

        # Check __all__ exports
        assert "SymphonyAdapterConfig" in symphony.__all__
        assert "SymphonyAdapter" in symphony.__all__
        assert "SymphonyMessage" in symphony.__all__
        assert "Presence" in symphony.__all__
        assert "mention_user_symphony" in symphony.__all__

    def test_backends_package_imports(self):
        """Test that backends package exports all modules."""
        from csp_bot import backends

        # Check that we can import from the package
        assert hasattr(backends, "DiscordAdapterManager")
        assert hasattr(backends, "SlackAdapterManager")
        assert hasattr(backends, "SymphonyAdapter")

        assert hasattr(backends, "DiscordMessage")
        assert hasattr(backends, "SlackMessage")
        assert hasattr(backends, "SymphonyMessage")


class TestDiscordMessageStruct:
    """Tests for DiscordMessage structure."""

    def test_discord_message_fields(self):
        """Test DiscordMessage has expected fields."""
        from csp_bot.backends.discord import DiscordMessage

        # Create a message to verify fields work
        msg = DiscordMessage(
            user="testuser",
            user_email="test@example.com",
            user_id="123456789012345678",
            tags=["111111111111111111"],
            channel="general",
            channel_id="222222222222222222",
            channel_type="public",
            msg="Hello world!",
            reaction="",
            thread="",
        )

        assert msg.user == "testuser"
        assert msg.user_email == "test@example.com"
        assert msg.user_id == "123456789012345678"
        assert msg.tags == ["111111111111111111"]
        assert msg.channel == "general"
        assert msg.channel_id == "222222222222222222"
        assert msg.msg == "Hello world!"


class TestSlackMessageStruct:
    """Tests for SlackMessage structure."""

    def test_slack_message_fields(self):
        """Test SlackMessage has expected fields."""
        from csp_bot.backends.slack import SlackMessage

        # Create a message to verify fields work
        msg = SlackMessage(
            user="testuser",
            user_email="test@example.com",
            user_id="U123456789",
            tags=["U987654321"],
            channel="general",
            channel_id="C123456789",
            channel_type="public",
            msg="Hello <@U987654321>!",
            reaction="",
            thread="",
            payload={},
        )

        assert msg.user == "testuser"
        assert msg.user_email == "test@example.com"
        assert msg.user_id == "U123456789"
        assert msg.tags == ["U987654321"]
        assert msg.channel == "general"
        assert msg.channel_id == "C123456789"
        assert msg.msg == "Hello <@U987654321>!"


class TestSymphonyMessageStruct:
    """Tests for SymphonyMessage structure."""

    def test_symphony_message_fields(self):
        """Test SymphonyMessage has expected fields."""
        from csp_bot.backends.symphony import SymphonyMessage

        # Create a message to verify fields work
        msg = SymphonyMessage(
            user="John Doe",
            user_email="john@example.com",
            user_id="123456789",
            tags=["987654321"],
            room="Test Room",
            msg="Hello world!",
            form_id="",
            form_values={},
        )

        assert msg.user == "John Doe"
        assert msg.user_email == "john@example.com"
        assert msg.user_id == "123456789"
        assert msg.tags == ["987654321"]
        assert msg.room == "Test Room"
        assert msg.msg == "Hello world!"


class TestMentionFunctions:
    """Tests for mention helper functions."""

    def test_mention_user_discord_available(self):
        """Test mention_user_discord function availability."""

        # Function should exist (may be None if adapter not installed)
        # Just verify it's exported
        assert "mention_user_discord" in dir(__import__("csp_bot.backends.discord", fromlist=["mention_user_discord"]))

    def test_mention_user_slack_available(self):
        """Test mention_user_slack function availability."""

        assert "mention_user_slack" in dir(__import__("csp_bot.backends.slack", fromlist=["mention_user_slack"]))

    def test_mention_user_symphony_available(self):
        """Test mention_user_symphony function availability."""

        assert "mention_user_symphony" in dir(__import__("csp_bot.backends.symphony", fromlist=["mention_user_symphony"]))
