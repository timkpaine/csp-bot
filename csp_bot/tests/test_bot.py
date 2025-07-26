from csp_bot import Bot, Message


class TestBot:
    def test_extract_bot_commands(self, bot: Bot):
        # TODO
        # commands = bot.extract_bot_commands(
        #     message=Message(
        #         user="user",
        #         msg="<@test_bot> /thanks <@user>",
        #         channel="test_channel",
        #         tags=["test_bot", "user"],
        #         backend="slack",
        #     ),
        #     channel="test_channel",
        #     text="<@test_bot> /thanks <@user>",
        #     entities=["test_bot", "user"],
        # )
        # assert commands is not None
        ...

    def test_extract_bot_commands_ignore_message(self, bot):
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

    def test_extract_bot_commands_bad_message(self, bot):
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

    def test_run_bot_command(self, bot): ...
