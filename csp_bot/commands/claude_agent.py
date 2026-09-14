import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from chatom.agent import BackendToolset

from csp_bot.commands.agent import AgentCommand


@dataclass(frozen=True)
class ClaudeRunResult:
    output: str
    session_id: str

    def all_messages(self) -> list[dict[str, str]]:
        """Return session state in the form persisted by AgentCommand."""
        return [{"type": "claude-session", "session_id": self.session_id}]


class ClaudeAgentRunner:
    """Run Claude with Chatom tools and resumable sessions."""

    def __init__(
        self,
        toolset: BackendToolset,
        *,
        model: str | None = None,
        query_fn: Any = None,
    ) -> None:
        if query_fn is None:
            from claude_agent_sdk import query

            query_fn = query
        self._toolset = toolset
        self._model = model
        self._query = query_fn

    async def run(
        self,
        prompt: str | Sequence[Any],
        *,
        session_id: str | None = None,
        message_history: Sequence[Any] | None = None,
    ) -> ClaudeRunResult:
        """Run one turn and return its output and resumable session ID."""
        from claude_agent_sdk import ResultError, ResultMessage

        if session_id is None and message_history:
            state = message_history[-1]
            if isinstance(state, dict) and state.get("type") == "claude-session":
                session_id = state.get("session_id")

        final_result = None
        options = await build_claude_options(
            self._toolset,
            model=self._model,
            resume=session_id,
        )
        claude_prompt = _claude_prompt(prompt)
        try:
            async for message in self._query(prompt=claude_prompt, options=options):
                if isinstance(message, ResultMessage):
                    final_result = message
        except ResultError as error:
            if final_result is None:
                raise RuntimeError("; ".join(error.errors) or str(error)) from error

        if final_result is None:
            raise RuntimeError("Claude query completed without a result")
        if final_result.is_error or final_result.subtype != "success":
            errors = final_result.errors or ([final_result.result] if final_result.result else [])
            raise RuntimeError("; ".join(errors) or f"Claude query failed: {final_result.subtype}")

        return ClaudeRunResult(
            output=final_result.result or "",
            session_id=final_result.session_id,
        )


class ClaudeAgentCommand(AgentCommand):
    """Agent command backed by the Claude Agent SDK."""

    def build_agent(self, command: Any) -> ClaudeAgentRunner:
        toolset = self.build_toolset(command)
        if toolset is None:
            raise RuntimeError("Claude agent command requires a connected backend")
        return ClaudeAgentRunner(toolset, model=self.model_name)


def _claude_prompt(prompt: str | Sequence[Any]) -> Any:
    if isinstance(prompt, str):
        return prompt

    from pydantic_ai import BinaryContent

    content = []
    for part in prompt:
        if isinstance(part, str):
            content.append({"type": "text", "text": part})
        elif isinstance(part, BinaryContent) and part.media_type.startswith("image/"):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": part.media_type,
                        "data": base64.b64encode(part.data).decode("ascii"),
                    },
                }
            )
        else:
            raise TypeError(f"Unsupported Claude prompt content: {type(part).__name__}")

    async def message_stream():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": content,
            },
        }

    return message_stream()


def _handler(toolset: BackendToolset, name: str, toolset_tool: Any = None):
    async def call(tool_args: dict[str, Any]) -> dict[str, Any]:
        call_tool = getattr(toolset, "call", None)
        if call_tool is not None:
            result = await call_tool(name, tool_args)
        else:
            validated_args = toolset_tool.args_validator.validate_python(tool_args)
            result = await toolset.call_tool(name, validated_args, cast(Any, None), toolset_tool)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result),
                }
            ]
        }

    return call


async def build_claude_tools(toolset: BackendToolset) -> list[Any]:
    """Convert a Chatom backend toolset to Claude SDK MCP tools."""
    from claude_agent_sdk import tool

    tool_definitions = getattr(toolset, "tool_definitions", None)
    if tool_definitions is not None:
        definitions = [(definition, None) for definition in tool_definitions().values()]
    else:
        toolset_tools = await toolset.get_tools(cast(Any, None))
        definitions = [(toolset_tool.tool_def, toolset_tool) for toolset_tool in toolset_tools.values()]

    tools = []
    for definition, toolset_tool in definitions:
        tools.append(
            tool(
                definition.name,
                definition.description or definition.name,
                definition.parameters_json_schema,
            )(_handler(toolset, definition.name, toolset_tool))
        )
    return tools


async def build_claude_mcp_server(toolset: BackendToolset) -> Any:
    """Build an in-process Claude SDK MCP server for a Chatom backend."""
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server(
        name=toolset.id or "chatom",
        tools=await build_claude_tools(toolset),
    )


async def build_claude_options(
    toolset: BackendToolset,
    *,
    model: str | None = None,
    resume: str | None = None,
) -> Any:
    """Configure Claude to use only the supplied Chatom tools."""
    from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server

    server_name = toolset.id or "chatom"
    tools = await build_claude_tools(toolset)
    allowed_tools = [f"mcp__{server_name}__{tool.name}" for tool in tools]
    return ClaudeAgentOptions(
        tools=[],
        allowed_tools=allowed_tools,
        mcp_servers={
            server_name: create_sdk_mcp_server(
                name=server_name,
                tools=tools,
            )
        },
        strict_mcp_config=True,
        setting_sources=[],
        model=model,
        resume=resume,
    )
