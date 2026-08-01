from unittest.mock import MagicMock

from chatom import Message, User

from csp_bot.commands.status import StatusCommand
from csp_bot.structs import BotCommand


def _command() -> BotCommand:
    return BotCommand(
        backend="slack",
        command="status",
        args=(),
        channel_id="C1",
        channel_name="general",
        source=User(id="U1"),
        targets=(),
        message=Message(content="/status"),
    )


def test_status_preexecute_records_instance_adapters():
    command = StatusCommand()
    bot = MagicMock()
    bot._adapters = {"slack": object(), "symphony": object()}

    bot_command = _command()
    assert command.preexecute(bot_command, bot) is bot_command
    assert command._adapters == ["slack", "symphony"]


def test_status_execute_uses_aware_utc_timestamp():
    result = StatusCommand().execute(_command())

    assert result is not None
    assert "+00:00" in result.content
