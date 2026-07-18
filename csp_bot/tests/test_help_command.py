"""Tests for help command rendering."""

from types import SimpleNamespace

from chatom import Message, User

from csp_bot.commands.help import HelpCommand
from csp_bot.structs import BotCommand, CommandVariant


def _command(backend: str) -> BotCommand:
    return BotCommand(
        command="help",
        args=(),
        source=User(id="user1"),
        targets=(),
        channel_id="channel1",
        channel_name="general",
        backend=backend,
        variant=CommandVariant.REPLY,
        message=Message(id="msg1", content="!help"),
        delay=None,
        schedule="",
        times_run=0,
    )


def _commands():
    return {
        "ask": SimpleNamespace(name="Ask", help="Ask <anything> & get an answer", backends=[]),
        "help": SimpleNamespace(name="Help", help="Get help with bot commands", backends=[]),
    }


def test_help_discord_uses_list_not_markdown_table() -> None:
    result = HelpCommand().execute(_command("discord"), _commands())

    assert result.content.startswith("**Bot Commands Help**")
    assert "- `/ask` **Ask**: Ask <anything> & get an answer" in result.content
    assert "| Command" not in result.content


def test_help_slack_uses_list_not_code_block_table() -> None:
    result = HelpCommand().execute(_command("slack"), _commands())

    assert result.content.startswith("*Bot Commands Help*")
    assert "- `/ask` *Ask*: Ask <anything> & get an answer" in result.content
    assert "```" not in result.content


def test_help_telegram_uses_supported_html_list() -> None:
    result = HelpCommand().execute(_command("telegram"), _commands())

    assert result.content.startswith("<b>Bot Commands Help</b>")
    assert "- <code>/ask</code> <b>Ask</b>: Ask &lt;anything&gt; &amp; get an answer" in result.content
    assert "<table>" not in result.content


def test_help_symphony_keeps_table_rendering() -> None:
    result = HelpCommand().execute(_command("symphony"), _commands())

    assert "<h3>Bot Commands Help</h3>" in result.content
    assert "<table>" in result.content
