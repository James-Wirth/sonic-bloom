"""Anthropic Claude streaming provider."""

from __future__ import annotations

import json
from collections.abc import Generator

import anthropic

from sonic_bloom.providers import ToolCall, TurnResult


class AnthropicProvider:
    """Claude API streaming provider."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 1024):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def stream_turn(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
    ) -> Generator[str, None, TurnResult]:
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in tools
        ]

        tool_calls: list[ToolCall] = []
        partial_json: list[str] = []

        with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            tools=anthropic_tools,
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_calls.append(ToolCall(
                            id=event.content_block.id,
                            name=event.content_block.name,
                            input={},
                        ))
                        partial_json.append("")
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield event.delta.text
                    elif event.delta.type == "input_json_delta":
                        if partial_json:
                            partial_json[-1] += event.delta.partial_json

            response = stream.get_final_message()

        for tc, raw in zip(tool_calls, partial_json):
            tc.input = json.loads(raw) if raw else {}

        return TurnResult(
            content=[block.model_dump(exclude_none=True) for block in response.content],
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
        )

    def simple_completion(self, messages: list[dict], system: str | None = None) -> str:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text
