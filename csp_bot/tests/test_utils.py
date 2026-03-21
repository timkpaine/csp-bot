"""Tests for utility functions using chatom."""

import pytest
from chatom import User
from chatom.format import FormattedMessage

from csp_bot.utils import (
    format_message,
    format_with_message_ml,
    get_backend_format,
    is_valid_url,
    mention_user,
    mention_users,
    recursive_format_for_message_ml,
    sanitize_message,
)


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


class TestMessageMLFormatting:
    """Tests for Symphony MessageML formatting utilities."""

    def test_format_with_message_ml_escapes_ampersand(self):
        """Test that ampersand is escaped for MessageML."""
        result = format_with_message_ml("Tom & Jerry")
        assert "&#38;" in result
        assert "&" not in result.replace("&#38;", "")

    def test_format_with_message_ml_escapes_less_than(self):
        """Test that < is escaped for MessageML."""
        result = format_with_message_ml("a < b")
        assert "&lt;" in result
        assert "<" not in result.replace("&lt;", "")

    def test_format_with_message_ml_escapes_dollar_brace(self):
        """Test that ${ is escaped for MessageML."""
        result = format_with_message_ml("${variable}")
        assert "&#36;{" in result

    def test_format_with_message_ml_escapes_hash_brace(self):
        """Test that #{ is escaped for MessageML."""
        result = format_with_message_ml("#{expression}")
        assert "&#35;{" in result

    def test_format_with_message_ml_unescape(self):
        """Test unescaping from MessageML."""
        escaped = "Tom &#38; Jerry with &lt;tags"
        result = format_with_message_ml(escaped, to_message_ml=False)
        assert "Tom & Jerry" in result
        assert "<tags" in result

    def test_sanitize_message(self):
        """Test sanitize_message escapes for MessageML."""
        result = sanitize_message("Hello <world> & ${stuff}")
        assert "&lt;" in result
        assert "&#38;" in result
        assert "&#36;{" in result

    def test_recursive_format_for_message_ml_with_list(self):
        """Test recursive formatting with a list."""
        data = ["hello", "<world", "foo & bar"]
        result = recursive_format_for_message_ml(data)
        assert len(result) == 3
        assert "&lt;world" in result[1]
        assert "&#38;" in result[2]

    def test_recursive_format_for_message_ml_with_dict(self):
        """Test recursive formatting with a dict."""
        data = {"key": "<value", "nested": {"inner": "a & b"}}
        result = recursive_format_for_message_ml(data)
        assert "&lt;value" in result["key"]
        assert "&#38;" in result["nested"]["inner"]

    def test_recursive_format_for_message_ml_with_tuple(self):
        """Test recursive formatting with a tuple."""
        data = ("a", "<b", "c & d")
        result = recursive_format_for_message_ml(data)
        # Tuples become lists
        assert isinstance(result, list)
        assert "&lt;b" in result[1]

    def test_recursive_format_for_message_ml_with_set(self):
        """Test recursive formatting with a set."""
        data = {"<item"}
        result = recursive_format_for_message_ml(data)
        assert isinstance(result, list)
        assert "&lt;item" in result[0]


class TestGetBackendFormat:
    """Tests for get_backend_format function."""

    def test_get_backend_format_slack(self):
        """Test getting format for Slack."""
        from chatom.format import Format

        fmt = get_backend_format("slack")
        assert fmt == Format.SLACK_MARKDOWN

    def test_get_backend_format_symphony(self):
        """Test getting format for Symphony."""
        from chatom.format import Format

        fmt = get_backend_format("symphony")
        assert fmt == Format.SYMPHONY_MESSAGEML

    def test_get_backend_format_discord(self):
        """Test getting format for Discord."""
        from chatom.format import Format

        fmt = get_backend_format("discord")
        assert fmt == Format.DISCORD_MARKDOWN
