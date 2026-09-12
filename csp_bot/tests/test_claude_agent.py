import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from chatom import User
from chatom.agent import AccessPolicy, BackendToolset
from chatom.backend import BackendBase

from csp_bot.commands.agent import _run_agent
from csp_bot.commands.claude_agent import (
    ClaudeAgentCommand,
    ClaudeAgentRunner,
    build_claude_mcp_server,
    build_claude_options,
    build_claude_tools,
)


class ConcreteClaudeAgentCommand(ClaudeAgentCommand):
    def command(self):
        return "claude"

    def name(self):
        return "Claude"

    def help(self):
        return "Ask Claude"

    def build_prompt(self, command):
        return "hello"


def test_claude_agent_command_is_publicly_exported():
    from csp_bot.commands import ClaudeAgentCommand as ExportedClaudeAgentCommand

    assert ExportedClaudeAgentCommand is ClaudeAgentCommand


def _toolset(access_policy: AccessPolicy | None = None) -> BackendToolset:
    backend = MagicMock(spec=BackendBase)
    backend.name = "mock"
    backend.capabilities = MagicMock()
    backend.capabilities.supports.return_value = True
    backend.normalize_channel_id = lambda channel_id: channel_id
    backend.lookup_user = AsyncMock(return_value=User(id="U1", name="Alice"))
    return BackendToolset(backend, access_policy=access_policy)


def test_build_claude_tools_preserves_definitions_and_execution():
    tools = build_claude_tools(_toolset())
    tools_by_name = {tool.name: tool for tool in tools}

    assert "read_channel_history" in tools_by_name
    assert "lookup_user" in tools_by_name
    assert "properties" in tools_by_name["lookup_user"].input_schema

    result = asyncio.run(tools_by_name["lookup_user"].handler({"user": {"id": "U1"}}))
    payload = json.loads(result["content"][0]["text"])

    assert payload["id"] == "U1"
    assert payload["name"] == "Alice"


def test_build_claude_mcp_server_returns_sdk_server():
    server = build_claude_mcp_server(_toolset())

    assert server["type"] == "sdk"
    assert server["name"] == "chatom-mock"
    assert server["instance"] is not None


def test_claude_tool_execution_preserves_access_policy():
    policy = AccessPolicy(
        invoking_channel_id="C1",
        restrict_to_invoking_channel=True,
    )
    tools = build_claude_tools(_toolset(policy))
    read_history = next(tool for tool in tools if tool.name == "read_channel_history")

    result = asyncio.run(read_history.handler({"channel": {"id": "C2"}, "limit": 10}))
    payload = json.loads(result["content"][0]["text"])

    assert payload["error"] == "access_denied"


def test_build_claude_options_exposes_only_chatom_tools():
    options = build_claude_options(
        _toolset(),
        model="claude-sonnet-4-6",
        resume="session-id",
    )

    assert options.tools == []
    assert options.setting_sources == []
    assert options.strict_mcp_config is True
    assert options.model == "claude-sonnet-4-6"
    assert options.resume == "session-id"
    assert set(options.mcp_servers) == {"chatom-mock"}
    assert "mcp__chatom-mock__read_channel_history" in options.allowed_tools
    assert "mcp__chatom-mock__send_message" in options.allowed_tools


def test_claude_runner_returns_output_and_resumes_session():
    from claude_agent_sdk import ResultMessage

    seen_options = []

    async def fake_query(*, prompt, options):
        seen_options.append(options)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="next-session",
            result=f"answer: {prompt}",
        )

    runner = ClaudeAgentRunner(_toolset(), model="claude-sonnet-4-6", query_fn=fake_query)

    first = asyncio.run(runner.run("hello", session_id="prior-session"))
    second = asyncio.run(runner.run("follow-up", message_history=first.all_messages()))

    assert first.output == "answer: hello"
    assert first.session_id == "next-session"
    assert second.output == "answer: follow-up"
    assert seen_options[0].resume == "prior-session"
    assert seen_options[1].resume == "next-session"
    assert seen_options[0].model == "claude-sonnet-4-6"


def test_claude_runner_translates_multimodal_prompt():
    from claude_agent_sdk import ResultMessage
    from pydantic_ai import BinaryContent

    seen_messages = []

    async def fake_query(*, prompt, options):
        seen_messages.extend([message async for message in prompt])
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="image-session",
            result="image answer",
        )

    runner = ClaudeAgentRunner(_toolset(), query_fn=fake_query)

    result = asyncio.run(
        runner.run(
            [
                "describe this",
                BinaryContent(data=b"image-bytes", media_type="image/png"),
            ]
        )
    )

    assert result.output == "image answer"
    assert seen_messages == [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe this"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": "aW1hZ2UtYnl0ZXM=",
                        },
                    },
                ],
            },
        }
    ]


def test_claude_runner_raises_on_error_result():
    from claude_agent_sdk import ResultError, ResultMessage

    async def fake_query(*, prompt, options):
        yield ResultMessage(
            subtype="error_during_execution",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="failed-session",
            errors=["query failed"],
        )
        raise ResultError(
            "query failed",
            data={"terminal_reason": "api_error", "errors": ["query failed"]},
        )

    runner = ClaudeAgentRunner(_toolset(), query_fn=fake_query)

    with pytest.raises(RuntimeError, match="query failed"):
        asyncio.run(runner.run("hello"))


def test_claude_runner_works_through_agent_command_execution_bridge():
    from claude_agent_sdk import ResultMessage

    seen_options = []

    async def fake_query(*, prompt, options):
        seen_options.append(options)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id=f"session-{len(seen_options)}",
            result=prompt,
        )

    runner = ClaudeAgentRunner(_toolset(), query_fn=fake_query)

    first = _run_agent(runner, "first")
    second = _run_agent(runner, "second", message_history=first.all_messages())

    assert first.output == "first"
    assert second.output == "second"
    assert seen_options[0].resume is None
    assert seen_options[1].resume == "session-1"


def test_claude_agent_command_builds_runner_for_invocation_backend():
    toolset = _toolset()
    command = ConcreteClaudeAgentCommand(model_name="claude-sonnet-4-6")
    invocation = MagicMock()
    build_toolset = MagicMock(return_value=toolset)
    command.build_toolset = build_toolset

    runner = command.build_agent(invocation)

    assert isinstance(runner, ClaudeAgentRunner)
    assert runner._toolset is toolset
    assert runner._model == "claude-sonnet-4-6"


def test_claude_agent_command_requires_backend_toolset():
    command = ConcreteClaudeAgentCommand()
    command.build_toolset = MagicMock(return_value=None)

    with pytest.raises(RuntimeError, match="connected backend"):
        command.build_agent(MagicMock())
