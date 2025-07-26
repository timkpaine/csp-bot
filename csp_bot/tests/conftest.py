from unittest.mock import MagicMock, patch

import pytest
from csp import ts
from csp.impl.wiring import Edge
from csp_adapter_discord import DiscordAdapterConfig
from csp_adapter_slack import SlackAdapterConfig

from csp_bot import Bot, BotCommand, BotConfig, Channels, DiscordConfig, Message, SlackConfig


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
    with (
        patch("csp.unroll", return_value=Edge(ts[Message], None, 0)),
        patch("csp.flatten", return_value=Edge(ts[Message], None, 0)),
        patch("csp.timer", return_value=Edge(ts[Message], None, 0)),
        patch("csp_adapter_discord.adapter.DiscordAdapterManager.publish"),
        patch("csp_adapter_slack.adapter.SlackAdapterManager.publish"),
    ):
        bot.connect(channels=channels_mock)
        yield bot
