"""Tests for Bot class with example messages from Symphony, Slack, and Discord."""

from csp_bot import Bot, Message
from csp_bot.structs import BotCommand, CommandVariant, User

# ============================================================================
# Example raw messages from each backend
# ============================================================================


class TestMessageParsing:
    """Tests for Bot.parse_msg with different backend message formats."""

    def test_parse_symphony_message_with_entities(self, bot: Bot):
        """Test parsing Symphony message with entity mentions."""
        # Symphony messages use HTML with span entities
        msg = Message(
            user="John Doe",
            user_id="123456789",
            msg='<div data-format="PresentationML" data-version="2.0"><span class="entity" data-entity-id="0">@CSPBot</span> /help <span class="entity" data-entity-id="1">@Alice</span></div>',
            channel="Test Room",
            tags=["123456789", "987654321"],
            backend="symphony",
        )
        text, entities = Bot.parse_msg(msg)
        assert "/help" in text
        assert "@CSPBot" in text or "@Alice" in text
        assert len(entities) == 2

    def test_parse_symphony_plain_message(self, bot: Bot):
        """Test parsing Symphony plain text message."""
        msg = Message(
            user="John Doe",
            user_id="123456789",
            msg='<div data-format="PresentationML" data-version="2.0">Hello world</div>',
            channel="Test Room",
            tags=[],
            backend="symphony",
        )
        text, entities = Bot.parse_msg(msg)
        assert "Hello world" in text
        assert len(entities) == 0

    def test_parse_symphony_reply_message(self, bot: Bot):
        """Test parsing Symphony message that's a reply (has separator)."""
        msg = Message(
            user="John Doe",
            user_id="123456789",
            msg='<div>Original message_———————————<span class="entity" data-entity-id="0">@CSPBot</span> /help</div>',
            channel="Test Room",
            tags=["123456789"],
            backend="symphony",
        )
        text, entities = Bot.parse_msg(msg)
        # The reply separator should be handled
        assert "@CSPBot" in text or "/help" in text

    def test_parse_slack_message_with_mentions(self, bot: Bot):
        """Test parsing Slack message with user mentions."""
        # Slack uses <@USERID> format for mentions
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="<@U000BOT> /help <@U987654321>",
            channel="general",
            tags=["U000BOT", "U987654321"],
            backend="slack",
        )
        text, entities = Bot.parse_msg(msg)
        assert text == "<@U000BOT> /help <@U987654321>"
        assert len(entities) == 2
        assert "@U000BOT" in entities
        assert "@U987654321" in entities

    def test_parse_slack_plain_message(self, bot: Bot):
        """Test parsing Slack plain text message."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="Hello world without mentions",
            channel="general",
            tags=[],
            backend="slack",
        )
        text, entities = Bot.parse_msg(msg)
        assert text == "Hello world without mentions"
        assert len(entities) == 0

    def test_parse_discord_message_with_mentions(self, bot: Bot):
        """Test parsing Discord message with user mentions."""
        # Discord also uses <@USERID> format
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="<@000000000000000001> /echo <@999999999999999999>",
            channel="general",
            tags=["000000000000000001", "999999999999999999"],
            backend="discord",
        )
        text, entities = Bot.parse_msg(msg)
        assert text == "<@000000000000000001> /echo <@999999999999999999>"
        assert len(entities) == 2
        assert "@000000000000000001" in entities
        assert "@999999999999999999" in entities

    def test_parse_discord_plain_message(self, bot: Bot):
        """Test parsing Discord plain text message."""
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="Just a regular message",
            channel="general",
            tags=[],
            backend="discord",
        )
        text, entities = Bot.parse_msg(msg)
        assert text == "Just a regular message"
        assert len(entities) == 0


class TestIsMsgToBot:
    """Tests for Bot.is_msg_to_bot detection logic."""

    def test_slack_message_with_bot_tag(self, bot: Bot):
        """Test detecting bot mention in Slack message."""
        # Bot tag is "UBOT123" as mocked in conftest
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="<@UBOT123> /help",
            channel="general",
            tags=["UBOT123"],
            backend="slack",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is True
        assert channel == msg.channel

    def test_slack_direct_message(self, bot: Bot):
        """Test DM detection for Slack."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="/help",
            channel="IM",
            tags=[],
            backend="slack",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        # DMs to bot should be detected
        assert is_to_bot is True
        assert channel == msg.user

    def test_discord_message_with_bot_tag(self, bot: Bot):
        """Test detecting bot mention in Discord message."""
        # Bot tag is "test_bot" for Discord
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="<@test_bot> /echo hello",
            channel="general",
            tags=["test_bot"],
            backend="discord",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is True

    def test_discord_direct_message(self, bot: Bot):
        """Test DM detection for Discord."""
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="/help",
            channel="IM",
            tags=[],
            backend="discord",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is True
        assert channel == msg.user

    def test_message_not_to_bot_slack(self, bot: Bot):
        """Test message not directed to bot in Slack."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="Just a regular chat message",
            channel="general",
            tags=[],
            backend="slack",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is False

    def test_message_not_to_bot_discord(self, bot: Bot):
        """Test message not directed to bot in Discord."""
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="Just a regular chat message",
            channel="general",
            tags=[],
            backend="discord",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is False


class TestBot:
    """Tests for Bot command extraction and execution."""

    def test_extract_bot_commands(self, bot: Bot):
        """Test extracting commands from message."""
        # This is a placeholder - proper test requires command registration
        ...

    def test_extract_bot_commands_ignore_message(self, bot: Bot):
        """Test that non-command messages are ignored."""
        commands = bot.extract_bot_commands(
            message=Message(
                user="user",
                msg="ignore",
                channel="test_channel",
                tags=[],
                backend="slack",
            ),
            channel="test_channel",
            text="ignore",
            entities=[],
        )
        assert commands is None

    def test_extract_bot_commands_bad_message(self, bot: Bot):
        """Test handling of malformed messages."""
        commands = bot.extract_bot_commands(
            message=Message(
                user="user",
                msg="\U00001010",
                channel="test_channel",
                tags=[],
                backend="slack",
            ),
            channel="test_channel",
            text="\U00001010",
            entities=[],
        )
        assert commands is None

    def test_extract_bot_commands_with_slash_command(self, bot: Bot):
        """Test extracting slash command from Slack message."""
        commands = bot.extract_bot_commands(
            message=Message(
                user="alice",
                user_id="U123456789",
                msg="/help",
                channel="general",
                tags=[],
                backend="slack",
            ),
            channel="general",
            text="/help",
            entities=[],
        )
        # help is a registered command
        assert commands is not None

    def test_extract_bot_commands_with_bot_prefix(self, bot: Bot):
        """Test command with @bot prefix."""
        commands = bot.extract_bot_commands(
            message=Message(
                user="alice",
                user_id="U123456789",
                msg="@test_bot /help",
                channel="general",
                tags=["test_bot"],
                backend="slack",
            ),
            channel="general",
            text="@test_bot /help",
            entities=[],
        )
        # Should recognize the help command
        assert commands is not None

    def test_extract_bot_commands_unregistered_command(self, bot: Bot):
        """Test that unregistered commands return None."""
        commands = bot.extract_bot_commands(
            message=Message(
                user="alice",
                user_id="U123456789",
                msg="/nonexistent_command",
                channel="general",
                tags=[],
                backend="slack",
            ),
            channel="general",
            text="/nonexistent_command",
            entities=[],
        )
        # Unregistered commands should return None
        assert commands is None

    def test_run_bot_command(self, bot: Bot):
        """Test running a bot command."""
        ...


class TestBotCommandsFromCommandString:
    """Tests for Bot.bot_commands_from_command_string parsing."""

    def test_simple_command(self, bot: Bot):
        """Test parsing a simple command without arguments."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/help",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/help"],
            message=msg,
            channel="general",
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert command == "help"
        assert args == []
        assert target_channel == "general"
        assert target_tags == []

    def test_command_with_arguments(self, bot: Bot):
        """Test parsing command with arguments."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo hello world",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "hello", "world"],
            message=msg,
            channel="general",
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert command == "echo"
        assert args == ["hello", "world"]
        assert target_channel == "general"

    def test_command_with_channel_override(self, bot: Bot):
        """Test parsing command with /channel directive."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo /channel other-room hello",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "/channel", "other-room", "hello"],
            message=msg,
            channel="general",
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert command == "echo"
        assert target_channel == "other-room"
        assert args == ["hello"]

    def test_command_with_room_override(self, bot: Bot):
        """Test parsing command with /room directive (deprecated)."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo /room other-room hello",
            channel="general",
            tags=[],
            backend="symphony",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "/room", "other-room", "hello"],
            message=msg,
            channel="general",
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert target_channel == "other-room"

    def test_command_with_entity_slack(self, bot: Bot):
        """Test parsing command with entity mentions for Slack."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo <@U456>",
            channel="general",
            tags=["Bob Smith"],  # Slack tags contain display names, not IDs
            backend="slack",
        )
        # For Slack: entity_text is "@USER_ID", tag_value is display name
        entity_map = {"ENTITY_0": ("@U456", "Bob Smith")}
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "ENTITY_0"],
            message=msg,
            channel="general",
            entity_map=entity_map,
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert command == "echo"
        assert len(target_tags) == 1
        # For Slack: id comes from entity_text (stripped @), name comes from tag_value
        assert target_tags[0].id == "U456"
        assert target_tags[0].name == "Bob Smith"

    def test_command_with_entity_symphony(self, bot: Bot):
        """Test parsing command with entity mentions for Symphony."""
        msg = Message(
            user="John",
            user_id="123456789",
            msg="<span class='entity'>@Alice</span>",
            channel="Test Room",
            tags=["987654321"],
            backend="symphony",
        )
        entity_map = {"ENTITY_0": ("@Alice", "987654321")}
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "ENTITY_0"],
            message=msg,
            channel="Test Room",
            entity_map=entity_map,
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert len(target_tags) == 1
        # Symphony order is (name, id) in entity_map
        assert target_tags[0].name == "@Alice"
        assert target_tags[0].id == "987654321"

    def test_command_with_entity_discord(self, bot: Bot):
        """Test parsing command with entity mentions for Discord."""
        msg = Message(
            user="bob",
            user_id="111111111111111111",
            msg="/echo <@222222222222222222>",
            channel="general",
            tags=["222222222222222222"],
            backend="discord",
        )
        entity_map = {"ENTITY_0": ("@bob", "222222222222222222")}
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "ENTITY_0"],
            message=msg,
            channel="general",
            entity_map=entity_map,
        )
        assert result is not None
        command, args, target_channel, target_tags = result
        assert len(target_tags) == 1

    def test_empty_tokens(self, bot: Bot):
        """Test handling of empty token list."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=[],
            message=msg,
            channel="general",
        )
        assert result is None

    def test_unregistered_command(self, bot: Bot):
        """Test handling of unregistered command."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/unknown_command",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/unknown_command"],
            message=msg,
            channel="general",
        )
        assert result is None

    def test_malformed_channel_directive(self, bot: Bot):
        """Test handling of malformed /channel directive."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo /channel",
            channel="general",
            tags=[],
            backend="slack",
        )
        # /channel without a room name
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "/channel"],
            message=msg,
            channel="general",
        )
        # Should still return something, just with original channel
        assert result is not None


class TestIsAuthorized:
    """Tests for Bot.is_authorized authorization check."""

    def test_slack_always_authorized(self, bot: Bot):
        """Test that Slack users are always authorized (not implemented)."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="/help",
            channel="general",
            tags=[],
            backend="slack",
        )
        assert bot.is_authorized(msg) is True

    def test_discord_always_authorized(self, bot: Bot):
        """Test that Discord users are always authorized (not implemented)."""
        msg = Message(
            user="bob",
            user_id="123456789012345678",
            msg="/help",
            channel="general",
            tags=[],
            backend="discord",
        )
        assert bot.is_authorized(msg) is True


class TestHelpCommand:
    """Tests for help command execution."""

    def test_help_command_execution(self, bot: Bot):
        """Test that help command returns a message."""
        command_instance = BotCommand(
            command="help",
            args=tuple(),
            source=User(name="alice", id="U123", backend="slack"),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(
                user="alice",
                user_id="U123",
                msg="/help",
                channel="general",
                tags=[],
                backend="slack",
            ),
        )
        result = bot.run_bot_command(command_instance)
        assert result is not None
        # Help command returns messages
        assert len(result) >= 1
        assert all(isinstance(r, Message) for r in result)

    def test_help_command_for_specific_command(self, bot: Bot):
        """Test help for a specific command."""
        command_instance = BotCommand(
            command="help",
            args=("echo",),
            source=User(name="alice", id="U123", backend="slack"),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(
                user="alice",
                user_id="U123",
                msg="/help echo",
                channel="general",
                tags=[],
                backend="slack",
            ),
        )
        result = bot.run_bot_command(command_instance)
        assert result is not None


class TestEchoCommand:
    """Tests for echo command execution."""

    def test_echo_command_execution(self, bot: Bot):
        """Test that echo command echoes the message."""
        command_instance = BotCommand(
            command="echo",
            args=("hello", "world"),
            source=User(name="alice", id="U123", backend="slack"),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(
                user="alice",
                user_id="U123",
                msg="/echo hello world",
                channel="general",
                tags=[],
                backend="slack",
            ),
        )
        result = bot.run_bot_command(command_instance)
        assert result is not None
        # Echo command should return the echoed message
        assert len(result) >= 1
        response_text = result[0].msg
        assert "hello" in response_text or "world" in response_text


class TestStatusCommand:
    """Tests for status command execution."""

    def test_status_command_execution(self, bot: Bot):
        """Test that status command returns bot status."""
        command_instance = BotCommand(
            command="status",
            args=tuple(),
            source=User(name="alice", id="U123", backend="slack"),
            channel="general",
            backend="slack",
            variant=CommandVariant.REPLY,
            message=Message(
                user="alice",
                user_id="U123",
                msg="/status",
                channel="general",
                tags=[],
                backend="slack",
            ),
        )
        # Status command requires preexecute to set _adapters
        # Call preexecute first to set up the command state
        status_cmd = bot._commands["status"]
        status_cmd.preexecute(command_instance, bot)
        result = bot.run_bot_command(command_instance)
        assert result is not None


class TestBotEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_msg_empty_message(self, bot: Bot):
        """Test parsing empty message."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="",
            channel="general",
            tags=[],
            backend="slack",
        )
        text, entities = Bot.parse_msg(msg)
        assert text == ""
        assert len(entities) == 0

    def test_parse_msg_only_whitespace(self, bot: Bot):
        """Test parsing whitespace-only message."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="   ",
            channel="general",
            tags=[],
            backend="slack",
        )
        text, entities = Bot.parse_msg(msg)
        assert text.strip() == ""

    def test_is_msg_to_bot_with_at_prefix(self, bot: Bot):
        """Test bot detection with @bot_name format (no angle brackets)."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="@UBOT123 /help",
            channel="general",
            tags=["UBOT123"],
            backend="slack",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is True

    def test_extract_commands_with_multiple_entities(self, bot: Bot):
        """Test command extraction with multiple user mentions."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo <@U456> <@U789>",
            channel="general",
            tags=["U456", "U789"],
            backend="slack",
        )
        commands = bot.extract_bot_commands(
            message=msg,
            channel="general",
            text="/echo <@U456> <@U789>",
            entities=["@U456", "@U789"],
        )
        assert commands is not None

    def test_extract_commands_with_dm_channel_detection(self, bot: Bot):
        """Test that DM channel triggers is_to_bot."""
        msg = Message(
            user="alice",
            user_id="U123456789",
            msg="/echo test",
            channel="IM",
            tags=[],
            backend="slack",
        )
        is_to_bot, channel, text, entities = bot.is_msg_to_bot(msg)
        assert is_to_bot is True
        # Channel should be set to user for DMs
        assert channel == "alice"

    def test_command_with_at_entity_malformed_room(self, bot: Bot):
        """Test command with /room followed by @user (malformed)."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo /room @someone",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "/room", "@someone"],
            message=msg,
            channel="general",
        )
        # Should still return result, just with original channel
        assert result is not None
        command, args, target_channel, _ = result
        assert command == "echo"

    def test_command_with_at_entity_malformed_channel(self, bot: Bot):
        """Test command with /channel followed by @user (malformed)."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo /channel @someone",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "/channel", "@someone"],
            message=msg,
            channel="general",
        )
        # Should still return result, just with original channel
        assert result is not None
        command, args, target_channel, _ = result
        assert command == "echo"

    def test_command_with_trailing_args(self, bot: Bot):
        """Test command with multiple trailing arguments."""
        msg = Message(
            user="alice",
            user_id="U123",
            msg="/echo hello world how are you",
            channel="general",
            tags=[],
            backend="slack",
        )
        result = bot.bot_commands_from_command_string(
            tokens=["/echo", "hello", "world", "how", "are", "you"],
            message=msg,
            channel="general",
        )
        assert result is not None
        command, args, target_channel, _ = result
        assert command == "echo"
        assert args == ["hello", "world", "how", "are", "you"]


class TestScheduleCommand:
    """Tests for schedule command basics."""

    def test_schedule_command_registered(self, bot: Bot):
        """Test that schedule command is registered."""
        assert "schedule" in bot._commands

    def test_schedule_command_help(self, bot: Bot):
        """Test schedule command help text."""
        schedule_cmd = bot._commands["schedule"]
        help_text = schedule_cmd.help()
        assert "schedule" in help_text.lower()
