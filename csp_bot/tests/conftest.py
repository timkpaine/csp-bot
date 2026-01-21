from unittest.mock import MagicMock, patch

import pytest
from csp import ts
from csp.impl.wiring import Edge
from csp_adapter_discord import DiscordAdapterConfig
from csp_adapter_slack import SlackAdapterConfig

from csp_bot import Bot, BotCommand, BotConfig, Channels, DiscordConfig, Message, SlackConfig
from csp_bot.commands import (
    EchoCommandModel,
    HelpCommandModel,
    ScheduleCommandModel,
    StatusCommandModel,
)


@pytest.fixture(scope="session")
def bot_config():
    return BotConfig(
        discord_config=DiscordConfig(
            bot_name="test_bot",
            adapter_config=DiscordAdapterConfig(
                token="1" * 72,
            ),
        ),
        slack_config=SlackConfig(
            bot_name="test_bot",
            adapter_config=SlackAdapterConfig(
                app_token="xapp-blerg",
                bot_token="xoxb-blerg",
            ),
        ),
    )


@pytest.fixture(scope="session")
def bot(bot_config):
    bot = Bot(config=bot_config)
    channels_mock = MagicMock(spec=Channels)

    def side_effect(name):
        if name == "commands":
            return Edge(ts[BotCommand], None, 0)
        raise Exception(name)

    channels_mock.get_channel.side_effect = side_effect

    # Create a mock adapter that returns a known bot tag
    mock_slack_adapter = MagicMock()
    mock_slack_adapter._get_user_from_name.return_value = "UBOT123"

    mock_discord_adapter = MagicMock()

    with (
        patch("csp.unroll", return_value=Edge(ts[Message], None, 0)),
        patch("csp.flatten", return_value=Edge(ts[Message], None, 0)),
        patch("csp.timer", return_value=Edge(ts[Message], None, 0)),
        patch("csp_adapter_discord.adapter.DiscordAdapterManager.publish"),
        patch("csp_adapter_slack.adapter.SlackAdapterManager.publish"),
    ):
        bot.connect(channels=channels_mock)

        # Patch adapters after connect to provide bot tag support
        bot._adapters["slack"] = mock_slack_adapter
        bot._adapters["discord"] = mock_discord_adapter

        # Load default commands
        bot.load_commands(
            [
                HelpCommandModel(),
                EchoCommandModel(),
                StatusCommandModel(),
                ScheduleCommandModel(),
            ]
        )

        yield bot


@pytest.fixture(scope="function")
def bot_with_symphony():
    """Bot fixture with Symphony config for testing Symphony-specific behavior."""
    # Create a minimal bot config without Symphony (we'll mock it)
    bot_config = BotConfig()
    bot = Bot(config=bot_config)

    # Create a mock symphony config with just the bot_name we need
    mock_symphony_config = MagicMock()
    mock_symphony_config.bot_name = "Cubist Bot"  # Shorter name to test against "Cubist Bot Dev"

    # Mock the symphony adapter
    mock_symphony_adapter = MagicMock()
    bot._adapters["symphony"] = mock_symphony_adapter
    bot._configs["symphony"] = mock_symphony_config

    # Load default commands
    bot.load_commands(
        [
            HelpCommandModel(),
            EchoCommandModel(),
            StatusCommandModel(),
            ScheduleCommandModel(),
        ]
    )

    yield bot
