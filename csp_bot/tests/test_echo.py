"""Tests for the echo command."""

from chatom import Channel, User

from csp_bot.commands.echo import EchoCommand, EchoCommandModel
from csp_bot.structs import BotCommand, CommandVariant


class TestEchoCommand:
    """Tests for the EchoCommand class."""

    def test_command_name(self):
        """Test the command name."""
        cmd = EchoCommand()
        assert cmd.command() == "echo"

    def test_name(self):
        """Test the display name."""
        cmd = EchoCommand()
        assert cmd.name() == "Echo"

    def test_help_text(self):
        """Test the help text."""
        cmd = EchoCommand()
        help_text = cmd.help()
        assert "echo" in help_text.lower()
        assert "<message>" in help_text

    def test_execute_with_args(self):
        """Test executing echo with arguments."""
        cmd = EchoCommand()
        channel = Channel(id="ch1", name="test-channel")
        bot_cmd = BotCommand(
            backend="slack",
            command="echo",
            args=("hello", "world"),
            channel_id=channel.id,
            channel_name=channel.name,
            source=User(id="u1", name="sender"),
            targets=(),
            variant=CommandVariant.REPLY,
            message=None,
        )

        result = cmd.execute(bot_cmd)

        assert result is not None
        assert result.content == "hello world"
        assert result.channel == channel
        assert result.metadata.get("backend") == "slack"

    def test_execute_with_no_args_returns_none(self):
        """Test executing echo with no arguments returns None."""
        cmd = EchoCommand()
        channel = Channel(id="ch1", name="test-channel")
        bot_cmd = BotCommand(
            backend="slack",
            command="echo",
            args=(),
            channel_id=channel.id,
            channel_name=channel.name,
            source=User(id="u1", name="sender"),
            targets=(),
            variant=CommandVariant.REPLY,
            message=None,
        )

        result = cmd.execute(bot_cmd)

        assert result is None

    def test_execute_with_targets(self):
        """Test executing echo with targets."""
        cmd = EchoCommand()
        channel = Channel(id="ch1", name="test-channel")

        target = User(id="u123", name="testuser")

        bot_cmd = BotCommand(
            backend="slack",
            command="echo",
            args=("hello",),
            channel_id=channel.id,
            channel_name=channel.name,
            source=User(id="u1", name="sender"),
            targets=(target,),
            variant=CommandVariant.REPLY_TO_OTHER,
            message=None,
        )

        result = cmd.execute(bot_cmd)

        assert result is not None
        assert "hello" in result.content
        # Slack mention format
        assert "<@u123>" in result.content or "testuser" in result.content

    def test_execute_with_only_targets(self):
        """Test executing echo with only targets (no args)."""
        cmd = EchoCommand()
        channel = Channel(id="ch1", name="test-channel")

        target = User(id="u123", name="testuser")

        bot_cmd = BotCommand(
            backend="slack",
            command="echo",
            args=(),
            channel_id=channel.id,
            channel_name=channel.name,
            source=User(id="u1", name="sender"),
            targets=(target,),
            variant=CommandVariant.REPLY_TO_OTHER,
            message=None,
        )

        result = cmd.execute(bot_cmd)

        assert result is not None
        # Should contain the mention
        assert "<@u123>" in result.content or "testuser" in result.content


class TestEchoCommandModel:
    """Tests for the EchoCommandModel."""

    def test_model_command_type(self):
        """Test that the model has the correct command type."""
        assert EchoCommandModel.model_fields["command"].default == EchoCommand

    def test_model_instantiation(self):
        """Test that the model can be instantiated."""
        model = EchoCommandModel()
        assert model.command == EchoCommand
