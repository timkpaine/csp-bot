"""Tests for the new command framework (Phase 1).

Tests the @command decorator, Command base class, CommandContext,
four execution signatures (sync, async, generator, async generator),
the executor, and the legacy adapter.
"""

import asyncio

import pytest
from chatom import Channel, Message, User
from chatom.format import Bold, FormattedMessage, Text, UserMention

from csp_bot.commands.base import ReplyToOtherCommand
from csp_bot.commands.context import BotInfo, CommandContext
from csp_bot.commands.executor import _coerce_response, execute_command_func
from csp_bot.commands.framework import Command, clear_registry, command, get_registered_commands
from csp_bot.commands.legacy import LegacyCommandAdapter
from csp_bot.structs import BotCommand, CommandVariant


def _make_ctx(**overrides) -> CommandContext:
    """Build a CommandContext with sensible defaults."""
    defaults = dict(
        command_name="test",
        source=User(id="U1", name="alice"),
        targets=[User(id="U2", name="bob")],
        channel=Channel(id="C1", name="general"),
        message=Message(content="/test hello", channel_id="C1"),
        args=["hello"],
        args_text="hello",
        backend="slack",
        bot=BotInfo(id="B1", name="testbot", version="0.0.1"),
        deps=None,
    )
    defaults.update(overrides)
    return CommandContext(**defaults)


class TestCommandContext:
    def test_basic_attributes(self):
        ctx = _make_ctx()
        assert ctx.command_name == "test"
        assert ctx.source.id == "U1"
        assert ctx.backend == "slack"
        assert ctx.args == ["hello"]
        assert ctx.args_text == "hello"

    def test_target_property(self):
        ctx = _make_ctx()
        assert ctx.target.id == "U2"

    def test_target_none_when_empty(self):
        ctx = _make_ctx(targets=[])
        assert ctx.target is None

    def test_mention_returns_user_mention(self):
        ctx = _make_ctx()
        node = ctx.mention(ctx.source)
        assert isinstance(node, UserMention)
        assert node.user_id == "U1"

    def test_mention_none_returns_empty(self):
        ctx = _make_ctx()
        node = ctx.mention(None)
        assert isinstance(node, UserMention)
        assert node.user_id == ""

    def test_reply_builds_formatted_message(self):
        ctx = _make_ctx()
        msg = ctx.reply("hello ", Bold(child=Text(content="world")))
        assert isinstance(msg, FormattedMessage)
        assert len(msg.content) == 2
        assert isinstance(msg.content[0], Text)
        assert isinstance(msg.content[1], Bold)

    def test_reply_sets_backend_metadata(self):
        ctx = _make_ctx(backend="symphony")
        msg = ctx.reply("test")
        assert msg.metadata["backend"] == "symphony"

    def test_reply_renders_for_backend(self):
        ctx = _make_ctx(backend="slack")
        msg = ctx.reply(Bold(child=Text(content="hi")))
        rendered = msg.render_for("slack")
        assert "*hi*" in rendered

    def test_table_from_dicts(self):
        ctx = _make_ctx()
        tbl = ctx.table([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        # Should produce a valid Table node
        rendered = tbl.render("markdown")
        assert "a" in rendered
        assert "1" in rendered

    def test_image(self):
        ctx = _make_ctx()
        img = ctx.image("https://example.com/img.png", alt="pic")
        assert img.url == "https://example.com/img.png"
        assert img.alt_text == "pic"

    def test_deps_accessible(self):
        ctx = _make_ctx(deps={"api_key": "abc"})
        assert ctx.deps["api_key"] == "abc"


class TestCommandDecorator:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    def test_registers_function(self):
        @command(name="ping", help="Pong!")
        def ping(ctx):
            return "pong"

        reg = get_registered_commands()
        assert "ping" in reg
        assert reg["ping"].help == "Pong!"
        assert reg["ping"].handler is ping

    def test_function_metadata(self):
        @command(name="greet", help="Say hello", backends=["slack"])
        def greet(ctx):
            return "hello"

        assert greet._command_name == "greet"
        assert greet._command_help == "Say hello"
        assert greet._command_backends == ["slack"]

    def test_multiple_commands(self):
        @command(name="a", help="A")
        def cmd_a(ctx):
            return "a"

        @command(name="b", help="B")
        def cmd_b(ctx):
            return "b"

        reg = get_registered_commands()
        assert "a" in reg
        assert "b" in reg

    def test_decorator_returns_original_function(self):
        @command(name="echo", help="Echo")
        def echo(ctx):
            return ctx.args_text

        # Should be callable directly
        ctx = _make_ctx(args_text="hello world")
        assert echo(ctx) == "hello world"


class TestCommandClass:
    def test_subclass_with_fields(self):
        class MyCmd(Command):
            name: str = "mycmd"
            help: str = "My command"
            multiplier: int = 2

            def execute(self, ctx):
                return str(int(ctx.args[0]) * self.multiplier)

        cmd = MyCmd()
        assert cmd.name == "mycmd"
        assert cmd.multiplier == 2

        ctx = _make_ctx(args=["5"])
        assert cmd.execute(ctx) == "10"

    def test_subclass_with_custom_fields(self):
        class Greeter(Command):
            name: str = "greet"
            help: str = "Greet someone"
            greeting: str = "Hello"

            def execute(self, ctx):
                return f"{self.greeting}, {ctx.source.name}!"

        cmd = Greeter(greeting="Howdy")
        ctx = _make_ctx()
        assert cmd.execute(ctx) == "Howdy, alice!"

    def test_base_command_raises_not_implemented(self):
        cmd = Command(name="noop", help="noop")
        ctx = _make_ctx()
        with pytest.raises(NotImplementedError):
            cmd.execute(ctx)


class TestExecutorSync:
    def test_sync_returns_str(self):
        def echo(ctx):
            return ctx.args_text

        ctx = _make_ctx(args_text="hello")
        results = execute_command_func(echo, ctx)
        assert len(results) == 1
        assert results[0].content == "hello"

    def test_sync_returns_message(self):
        def echo(ctx):
            return Message(content="hi", metadata={"backend": "slack"})

        ctx = _make_ctx()
        results = execute_command_func(echo, ctx)
        assert results[0].content == "hi"

    def test_sync_returns_formatted_message(self):
        def echo(ctx):
            return ctx.reply(Bold(child=Text(content="bold")))

        ctx = _make_ctx(backend="slack")
        results = execute_command_func(echo, ctx)
        assert results[0].content == "*bold*"

    def test_sync_returns_none(self):
        def noop(ctx):
            return None

        ctx = _make_ctx()
        results = execute_command_func(noop, ctx)
        assert results == [None]

    def test_sync_returns_bot_command(self):
        def next_cmd(ctx):
            return BotCommand(
                command="followup",
                args=("x",),
                source=ctx.source,
                targets=tuple(ctx.targets),
                channel_id=ctx.channel.id,
                channel_name=ctx.channel.name,
                backend=ctx.backend,
                variant=CommandVariant.REPLY_TO_OTHER,
                message=ctx.message,
                delay=None,
                schedule="",
                times_run=0,
            )

        ctx = _make_ctx()
        results = execute_command_func(next_cmd, ctx)
        assert len(results) == 1
        assert isinstance(results[0], BotCommand)
        assert results[0].command == "followup"

    def test_sync_raises(self):
        def bad(ctx):
            raise ValueError("boom")

        ctx = _make_ctx()
        with pytest.raises(ValueError, match="boom"):
            execute_command_func(bad, ctx)


class TestExecutorAsync:
    def test_async_returns_str(self):
        async def echo(ctx):
            return ctx.args_text

        ctx = _make_ctx(args_text="async hello")
        results = execute_command_func(echo, ctx)
        assert len(results) == 1
        assert results[0].content == "async hello"

    def test_async_returns_formatted(self):
        async def echo(ctx):
            return ctx.reply("async world")

        ctx = _make_ctx(backend="discord")
        results = execute_command_func(echo, ctx)
        assert results[0].content == "async world"

    def test_async_raises(self):
        async def bad(ctx):
            raise RuntimeError("async boom")

        ctx = _make_ctx()
        with pytest.raises(RuntimeError, match="async boom"):
            execute_command_func(bad, ctx)

    def test_async_returns_bot_command(self):
        async def next_cmd(ctx):
            return BotCommand(
                command="afollowup",
                args=(),
                source=ctx.source,
                targets=tuple(ctx.targets),
                channel_id=ctx.channel.id,
                channel_name=ctx.channel.name,
                backend=ctx.backend,
                variant=CommandVariant.REPLY_TO_OTHER,
                message=ctx.message,
                delay=None,
                schedule="",
                times_run=0,
            )

        ctx = _make_ctx()
        results = execute_command_func(next_cmd, ctx)
        assert len(results) == 1
        assert isinstance(results[0], BotCommand)
        assert results[0].command == "afollowup"


class TestExecutorGenerator:
    def test_generator_yields_multiple(self):
        def multi(ctx):
            yield "first"
            yield "second"
            yield "third"

        ctx = _make_ctx()
        results = execute_command_func(multi, ctx)
        assert len(results) == 3
        assert results[0].content == "first"
        assert results[1].content == "second"
        assert results[2].content == "third"

    def test_generator_stops_on_none_sentinel(self):
        def sparse(ctx):
            yield "a"
            yield None
            yield "b"

        ctx = _make_ctx()
        results = execute_command_func(sparse, ctx)
        assert len(results) == 1
        assert results[0].content == "a"

    def test_generator_stops_on_stopiteration(self):
        def finite(ctx):
            yield "x"
            yield "y"
            # Natural exhaustion -> StopIteration

        ctx = _make_ctx()
        results = execute_command_func(finite, ctx)
        assert len(results) == 2
        assert results[0].content == "x"
        assert results[1].content == "y"

    def test_generator_yields_bot_command(self):
        def next_cmd(ctx):
            yield "working"
            yield BotCommand(
                command="gfollowup",
                args=("1",),
                source=ctx.source,
                targets=tuple(ctx.targets),
                channel_id=ctx.channel.id,
                channel_name=ctx.channel.name,
                backend=ctx.backend,
                variant=CommandVariant.REPLY_TO_OTHER,
                message=ctx.message,
                delay=None,
                schedule="",
                times_run=0,
            )
            yield None

        ctx = _make_ctx()
        results = execute_command_func(next_cmd, ctx)
        assert len(results) == 2
        assert results[0].content == "working"
        assert isinstance(results[1], BotCommand)
        assert results[1].command == "gfollowup"

    def test_generator_yields_formatted(self):
        def rich(ctx):
            yield ctx.reply(Bold(child=Text(content="step 1")))
            yield ctx.reply(Bold(child=Text(content="step 2")))

        ctx = _make_ctx(backend="slack")
        results = execute_command_func(rich, ctx)
        assert len(results) == 2
        assert "*step 1*" in results[0].content
        assert "*step 2*" in results[1].content

    def test_generator_raises(self):
        def bad_gen(ctx):
            yield "ok"
            raise ValueError("gen boom")

        ctx = _make_ctx()
        with pytest.raises(ValueError, match="gen boom"):
            execute_command_func(bad_gen, ctx)


class TestExecutorAsyncGenerator:
    def test_async_generator_yields_multiple(self):
        async def multi(ctx):
            yield "first"
            yield "second"

        ctx = _make_ctx()
        results = execute_command_func(multi, ctx)
        assert len(results) == 2
        assert results[0].content == "first"
        assert results[1].content == "second"

    def test_async_generator_with_await(self):
        async def fetcher(ctx):
            await asyncio.sleep(0.01)
            yield "fetched"

        ctx = _make_ctx()
        results = execute_command_func(fetcher, ctx)
        assert len(results) == 1
        assert results[0].content == "fetched"

    def test_async_generator_stops_on_none_sentinel(self):
        async def sparse(ctx):
            yield "start"
            yield None
            yield "after"

        ctx = _make_ctx()
        results = execute_command_func(sparse, ctx)
        assert len(results) == 1
        assert results[0].content == "start"

    def test_async_generator_stops_on_exhaustion(self):
        async def finite(ctx):
            yield "x"
            yield "y"
            # Natural async generator exhaustion

        ctx = _make_ctx()
        results = execute_command_func(finite, ctx)
        assert len(results) == 2
        assert results[0].content == "x"
        assert results[1].content == "y"

    def test_async_generator_yields_bot_command(self):
        async def next_cmd(ctx):
            yield "working"
            yield BotCommand(
                command="agfollowup",
                args=(),
                source=ctx.source,
                targets=tuple(ctx.targets),
                channel_id=ctx.channel.id,
                channel_name=ctx.channel.name,
                backend=ctx.backend,
                variant=CommandVariant.REPLY_TO_OTHER,
                message=ctx.message,
                delay=None,
                schedule="",
                times_run=0,
            )
            yield None

        ctx = _make_ctx()
        results = execute_command_func(next_cmd, ctx)
        assert len(results) == 2
        assert results[0].content == "working"
        assert isinstance(results[1], BotCommand)
        assert results[1].command == "agfollowup"

    def test_async_generator_raises(self):
        async def bad_agen(ctx):
            yield "ok"
            raise RuntimeError("agen boom")

        ctx = _make_ctx()
        with pytest.raises(RuntimeError, match="agen boom"):
            execute_command_func(bad_agen, ctx)


class TestExecutorWithCommandClass:
    def test_sync_command_class(self):
        class Echo(Command):
            name: str = "echo"
            help: str = "Echo"

            def execute(self, ctx):
                return ctx.args_text

        cmd = Echo()
        ctx = _make_ctx(args_text="class hello")
        results = execute_command_func(cmd.execute, ctx)
        assert results[0].content == "class hello"

    def test_async_command_class(self):
        class AsyncEcho(Command):
            name: str = "aecho"
            help: str = "Async echo"

            async def execute(self, ctx):
                return ctx.args_text

        cmd = AsyncEcho()
        ctx = _make_ctx(args_text="async class")
        results = execute_command_func(cmd.execute, ctx)
        assert results[0].content == "async class"

    def test_generator_command_class(self):
        class MultiStep(Command):
            name: str = "multi"
            help: str = "Multi-step"

            def execute(self, ctx):
                yield "step 1"
                yield "step 2"

        cmd = MultiStep()
        ctx = _make_ctx()
        results = execute_command_func(cmd.execute, ctx)
        assert len(results) == 2

    def test_async_generator_command_class(self):
        class Streamer(Command):
            name: str = "stream"
            help: str = "Stream"

            async def execute(self, ctx):
                yield "chunk 1"
                yield "chunk 2"

        cmd = Streamer()
        ctx = _make_ctx()
        results = execute_command_func(cmd.execute, ctx)
        assert len(results) == 2


class TestCoerceResponse:
    def test_none(self):
        assert _coerce_response(None, "slack") is None

    def test_str(self):
        msg = _coerce_response("hello", "slack")
        assert isinstance(msg, Message)
        assert msg.content == "hello"
        assert msg.metadata["backend"] == "slack"

    def test_message_passthrough(self):
        m = Message(content="hi", metadata={"backend": "discord"})
        result = _coerce_response(m, "discord")
        assert result is m

    def test_message_sets_backend_if_missing(self):
        m = Message(content="hi")
        result = _coerce_response(m, "symphony")
        assert result.metadata["backend"] == "symphony"

    def test_formatted_message(self):
        fm = FormattedMessage(content=[Bold(child=Text(content="bold"))])
        result = _coerce_response(fm, "slack")
        assert isinstance(result, Message)
        assert "*bold*" in result.content
        assert result.metadata["backend"] == "slack"

    def test_formatted_message_with_image(self):
        from chatom.format.attachment import FormattedImage

        fm = FormattedMessage(
            content=[
                Text(content="Check this:"),
                FormattedImage(url="https://example.com/chart.png", alt_text="chart"),
            ]
        )
        result = _coerce_response(fm, "discord")
        assert isinstance(result, Message)
        assert len(result.attachments) == 1
        assert result.attachments[0].url == "https://example.com/chart.png"
        assert result.attachments[0].attachment_type.value == "image"

    def test_formatted_message_with_attachment(self):
        from chatom.format.attachment import FormattedAttachment

        fm = FormattedMessage(
            content=[Text(content="Here's the report:")],
            attachments=[
                FormattedAttachment(
                    filename="report.pdf",
                    url="https://example.com/report.pdf",
                    content_type="application/pdf",
                    size=2048,
                )
            ],
        )
        result = _coerce_response(fm, "slack")
        assert isinstance(result, Message)
        assert len(result.attachments) == 1
        att = result.attachments[0]
        assert att.filename == "report.pdf"
        assert att.url == "https://example.com/report.pdf"
        assert att.size == 2048

    def test_formatted_message_with_mixed_content_and_attachments(self):
        from chatom.format.attachment import FormattedAttachment, FormattedImage

        fm = FormattedMessage(
            content=[
                Text(content="Results:"),
                FormattedImage(url="https://example.com/img.png", alt_text="img"),
            ],
            attachments=[
                FormattedAttachment(
                    filename="data.csv",
                    url="https://example.com/data.csv",
                    content_type="text/csv",
                )
            ],
        )
        result = _coerce_response(fm, "symphony")
        assert isinstance(result, Message)
        assert len(result.attachments) == 2  # 1 image from content + 1 from attachments

    def test_formatted_message_preserves_binary_image_data(self):
        """Binary image bytes must survive so the send path can upload them."""
        from chatom.format.attachment import FormattedImage

        fm = FormattedMessage(
            content=[
                Text(content="Generated chart:"),
                FormattedImage(data=b"PNGBYTES", filename="chart.png", content_type="image/png"),
            ]
        )
        result = _coerce_response(fm, "slack")
        assert isinstance(result, Message)
        assert len(result.attachments) == 1
        att = result.attachments[0]
        assert att.has_data is True
        assert att.data == b"PNGBYTES"
        assert att.filename == "chart.png"
        assert att.content_type == "image/png"

    def test_formatted_message_preserves_binary_attachment_data(self):
        """Binary file bytes must survive for upload via the send path."""
        from chatom.format.attachment import FormattedAttachment

        fm = FormattedMessage(
            content=[Text(content="Report:")],
            attachments=[
                FormattedAttachment(filename="report.pdf", data=b"%PDF-1.7", content_type="application/pdf"),
            ],
        )
        result = _coerce_response(fm, "slack")
        assert isinstance(result, Message)
        assert len(result.attachments) == 1
        att = result.attachments[0]
        assert att.has_data is True
        assert att.data == b"%PDF-1.7"
        assert att.attachment_type.value == "document"

    def test_unknown_type(self):
        result = _coerce_response(42, "slack")
        assert isinstance(result, Message)
        assert result.content == "42"


class _FakeEchoCommand(ReplyToOtherCommand):
    """Minimal legacy command for testing."""

    def command(self):
        return "echo"

    def name(self):
        return "Echo"

    def help(self):
        return "Echo a message"

    def execute(self, cmd):
        content = " ".join(cmd.args) if cmd.args else ""
        return Message(content=content, metadata={"backend": cmd.backend})


class TestLegacyAdapter:
    def test_wraps_command(self):
        legacy = _FakeEchoCommand()
        adapter = LegacyCommandAdapter(legacy)
        assert adapter.name == "echo"
        assert adapter.help == "Echo a message"
        assert adapter.wrapped is legacy

    def test_execute_via_adapter(self):
        legacy = _FakeEchoCommand()
        adapter = LegacyCommandAdapter(legacy)
        ctx = _make_ctx(command_name="echo", args=["hello", "world"])
        result = adapter.execute(ctx)
        assert isinstance(result, Message)
        assert result.content == "hello world"

    def test_context_to_bot_command(self):
        legacy = _FakeEchoCommand()
        adapter = LegacyCommandAdapter(legacy)
        ctx = _make_ctx(
            command_name="echo",
            args=["x"],
            backend="symphony",
        )
        bot_cmd = adapter.context_to_bot_command(ctx)
        assert isinstance(bot_cmd, BotCommand)
        assert bot_cmd.command == "echo"
        assert bot_cmd.args == ("x",)
        assert bot_cmd.backend == "symphony"
        assert bot_cmd.variant == CommandVariant.REPLY_TO_OTHER


class TestEndToEnd:
    def setup_method(self):
        clear_registry()

    def teardown_method(self):
        clear_registry()

    def test_decorated_sync_through_executor(self):
        @command(name="greet", help="Greet")
        def greet(ctx):
            return f"Hello, {ctx.source.name}!"

        entry = get_registered_commands()["greet"]
        ctx = _make_ctx()
        results = execute_command_func(entry.handler, ctx)
        assert results[0].content == "Hello, alice!"

    def test_decorated_async_through_executor(self):
        @command(name="agreet", help="Async greet")
        async def agreet(ctx):
            return f"Hi, {ctx.source.name}!"

        entry = get_registered_commands()["agreet"]
        ctx = _make_ctx()
        results = execute_command_func(entry.handler, ctx)
        assert results[0].content == "Hi, alice!"

    def test_decorated_generator_through_executor(self):
        @command(name="multi", help="Multi")
        def multi(ctx):
            yield "one"
            yield "two"

        entry = get_registered_commands()["multi"]
        ctx = _make_ctx()
        results = execute_command_func(entry.handler, ctx)
        assert len(results) == 2

    def test_class_command_through_executor(self):
        class Thanks(Command):
            name: str = "thanks"
            help: str = "Thank someone"
            gifts: list = ["cookie", "cake"]

            def execute(self, ctx):
                return f"{ctx.mention(ctx.target)} gets a {self.gifts[0]}"

        cmd = Thanks()
        ctx = _make_ctx(backend="slack")
        results = execute_command_func(cmd.execute, ctx)
        # UserMention rendered as string when coerced
        assert "gets a cookie" in results[0].content

    def test_formatted_message_renders_per_backend(self):
        @command(name="rich", help="Rich")
        def rich(ctx):
            return ctx.reply(
                Bold(child=Text(content="Title")),
                " - details",
            )

        entry = get_registered_commands()["rich"]

        # Slack
        ctx_slack = _make_ctx(backend="slack")
        results = execute_command_func(entry.handler, ctx_slack)
        assert "*Title*" in results[0].content
        assert " - details" in results[0].content

        # Discord
        ctx_discord = _make_ctx(backend="discord")
        results = execute_command_func(entry.handler, ctx_discord)
        assert "**Title**" in results[0].content
