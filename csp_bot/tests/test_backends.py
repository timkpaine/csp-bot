"""Tests for backend modules."""


class TestBackendImports:
    """Tests for backend imports."""

    def test_slack_backend_imports(self):
        """Test Slack backend imports."""
        from csp_bot.backends.slack import SlackAdapter, SlackMessage

        assert SlackAdapter is not None
        assert SlackMessage is not None

    def test_symphony_backend_imports(self):
        """Test Symphony backend imports."""
        from csp_bot.backends.symphony import SymphonyAdapter, SymphonyMessage

        assert SymphonyAdapter is not None
        assert SymphonyMessage is not None


class TestChatomIntegration:
    """Tests for chatom integration."""

    def test_chatom_types_available(self):
        """Test that chatom types are available."""
        from chatom import Channel, Message, User

        assert Message is not None
        assert User is not None
        assert Channel is not None

    def test_chatom_mention_utils(self):
        """Test chatom mention utilities."""
        from chatom import User, mention_user_for_backend

        user = User(id="U123", name="Test")

        slack_mention = mention_user_for_backend(user, "slack")
        assert "<@U123>" in slack_mention

        symphony_mention = mention_user_for_backend(user, "symphony")
        assert "<mention uid=" in symphony_mention
