"""Pytest configuration for csp-bot tests."""

import pytest
from chatom.base import Channel, User

from csp_bot import BotConfig, Message
from csp_bot.bot_config import SlackConfig, SymphonyConfig


@pytest.fixture(scope="session")
def bot_config():
    """Create a basic bot config for testing.

    bot_name is empty - will be auto-detected from backend.
    """
    return BotConfig(
        slack=SlackConfig(),
        symphony=SymphonyConfig(),
    )


@pytest.fixture
def sample_message():
    """Create a sample chatom Message for testing."""
    return Message(
        id="msg123",
        content="Hello world",
        author=User(id="U123"),
        channel=Channel(id="C123"),
        backend="slack",
    )


@pytest.fixture
def sample_user():
    """Create a sample chatom User for testing."""
    return User(
        id="U123",
        name="John Doe",
        email="john@example.com",
        handle="jdoe",
    )
