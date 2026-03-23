"""OpenAI-compatible streaming provider (also covers Ollama)."""

from __future__ import annotations

import json
from collections.abc import Generator

from sonic_bloom.providers import ToolCall, TurnResult


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert neutral tool schemas to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def _to_openai_messages(messages: list[dict], system: str) -> list[dict]:
    """Convert Anthropic-format messages to OpenAI format.

    Key differences:
    - System prompt becomes a system message
    - Tool results (Anthropic content blocks) become separate tool messages
    """
    out: list[dict] = [{"role": "system", "content": system}]

    for msg in messages:
        if msg["role"] == "assistant":
            content_parts = msg.get("content", [])
            if isinstance(content_parts, str):
                out.append({"role": "assistant", "content": content_parts})
                continue

            text_parts = []
            tool_calls = []
            for block in content_parts:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })

            assistant_msg: dict = {"role": "assistant"}
            if text_parts:
                assistant_msg["content"] = "\n".join(text_parts)
            else:
                assistant_msg["content"] = None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            out.append(assistant_msg)

        elif msg["role"] == "user":
            content = msg.get("content")
            if isinstance(content, str):
                out.append({"role": "user", "content": content})
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        out.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block.get("content", ""),
                        })
                    else:
                        out.append({"role": "user", "content": str(block)})
        else:
            out.append(msg)

    return out


class OpenAIProvider:
    """OpenAI-compatible streaming provider. Works with OpenAI API and Ollama."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
        base_url: str | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI provider requires the 'openai' package. "
                "Install with: pip install sonic-bloom[openai]"
            )
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self._max_tokens = max_tokens

    def stream_turn(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
    ) -> Generator[str, None, TurnResult]:
        openai_messages = _to_openai_messages(messages, system)
        openai_tools = _to_openai_tools(tools)

        tool_calls_by_index: dict[int, dict] = {}
        text_content = ""

        stream = self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            tools=openai_tools,
            max_tokens=self._max_tokens,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if delta.content:
                text_content += delta.content
                yield delta.content

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_by_index:
                        tool_calls_by_index[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    entry = tool_calls_by_index[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["arguments"] += tc_delta.function.arguments

        finish_reason = "end_turn"
        if chunk and chunk.choices:
            fr = chunk.choices[0].finish_reason
            if fr == "tool_calls":
                finish_reason = "tool_use"

        content: list[dict] = []
        if text_content:
            content.append({"type": "text", "text": text_content})

        parsed_tool_calls: list[ToolCall] = []
        for idx in sorted(tool_calls_by_index):
            entry = tool_calls_by_index[idx]
            tc = ToolCall(
                id=entry["id"],
                name=entry["name"],
                input=json.loads(entry["arguments"]) if entry["arguments"] else {},
            )
            parsed_tool_calls.append(tc)
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input,
            })

        return TurnResult(
            content=content,
            tool_calls=parsed_tool_calls,
            stop_reason=finish_reason,
        )

    def simple_completion(self, messages: list[dict], system: str | None = None) -> str:
        openai_messages: list[dict] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                openai_messages.append({"role": msg["role"], "content": content})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content or ""
