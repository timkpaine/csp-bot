"""Tests for utility functions using chatom."""

import pytest
from chatom import User
from chatom.format import FormattedMessage

from csp_bot.utils import format_message, is_valid_url, mention_user, mention_users


class TestMentionUtils:
    """Tests for mention utility functions."""

    def test_mention_user_slack(self):
        """Test mentioning User for Slack."""
        user = User(
            id="U123",
            name="John",
        )
        result = mention_user(user, "slack")
        assert "<@U123>" in result

    def test_mention_user_symphony(self):
        """Test mentioning User for Symphony."""
        user = User(
            id="12345",
            name="John",
        )
        result = mention_user(user, "symphony")
        assert "<mention uid=" in result
        assert "12345" in result

    def test_mention_chatom_user(self):
        """Test mentioning chatom User directly."""
        user = User(id="U999", name="Test")
        result = mention_user(user, "slack")
        assert "<@U999>" in result

    def test_mention_multiple_users(self):
        """Test mentioning multiple users."""
        users = [
            User(id="U1", name="A"),
            User(id="U2", name="B"),
        ]
        result = mention_users(users, "slack")
        assert "<@U1>" in result
        assert "<@U2>" in result

    def test_mention_user_requires_user_object_not_string(self):
        """Test that mention_user raises error when given a string instead of User.

        This catches the common mistake of passing user.id instead of user.
        """
        with pytest.raises(AttributeError, match="'str' object has no attribute 'id'"):
            mention_user("U123", "slack")  # Wrong: passing string instead of User

    def test_mention_user_requires_user_object_not_id(self):
        """Test that passing a user ID string fails with a clear error."""
        user = User(id="U123", name="John")
        # This is correct - pass the user object
        result = mention_user(user, "slack")
        assert "<@U123>" in result

        # This is wrong - passing user.id instead of user
        with pytest.raises(AttributeError):
            mention_user(user.id, "slack")


class TestFormatUtils:
    """Tests for format utility functions."""

    def test_format_plain_text(self):
        """Test formatting plain text."""
        result = format_message("Hello world", "slack")
        assert result == "Hello world"

    def test_format_with_formatted_message_slack(self):
        """Test formatting with FormattedMessage for Slack."""
        fmt = FormattedMessage()
        fmt.add_bold("bold")
        result = format_message("", "slack", fmt)
        assert "*bold*" in result

    def test_format_with_formatted_message_symphony(self):
        """Test formatting with FormattedMessage for Symphony."""
        fmt = FormattedMessage()
        fmt.add_bold("bold")
        result = format_message("", "symphony", fmt)
        assert "<b>bold</b>" in result


class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_urls(self):
        """Test valid URLs."""
        assert is_valid_url("https://example.com")
        assert is_valid_url("http://localhost:8080")

    def test_invalid_urls(self):
        """Test invalid URLs."""
        assert not is_valid_url("not-a-url")
        assert not is_valid_url("")
