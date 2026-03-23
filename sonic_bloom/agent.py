"""Provider-agnostic streaming tool-use agent."""

from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass

from sonic_bloom.providers import Provider, TurnResult
from sonic_bloom.tools import get_tools, execute
from sonic_bloom.soul.prompts import build_system

MAX_TOOL_ITERATIONS = 10


@dataclass(slots=True)
class TextDelta:
    text: str

@dataclass(slots=True)
class ToolStart:
    name: str

@dataclass(slots=True)
class ToolEnd:
    name: str
    result: dict | None = None
    error: str | None = None

@dataclass(slots=True)
class AskUser:
    question: str
    tool_call_id: str
    options: list[str] | None = None

AgentEvent = TextDelta | ToolStart | ToolEnd | AskUser


class MusicAgent:
    """Streaming tool-use agent backed by any Provider."""

    def __init__(self, provider: Provider, soul_content: str | None = None):
        self._provider = provider
        self._soul_content = soul_content
        self._messages: list[dict] = []

    def chat(self, user_input: str) -> Generator[AgentEvent, str | None, None]:
        """Send a message and yield events as they stream back.

        Yields AgentEvent instances. When an AskUser event is yielded,
        the caller must .send() the user's answer string to resume.
        """
        self._messages.append({"role": "user", "content": user_input})
        yield from self._run_turn()

    def _run_turn(self) -> Generator[AgentEvent, str | None, None]:
        system = build_system(self._soul_content)
        tools = get_tools()
        for _ in range(MAX_TOOL_ITERATIONS):
            result: TurnResult = yield from self._wrap_stream(
                self._provider.stream_turn(
                    messages=self._messages,
                    system=system,
                    tools=tools,
                )
            )

            self._messages.append({"role": "assistant", "content": result.content})

            if result.stop_reason != "tool_use":
                return

            tool_results = []
            for call in result.tool_calls:
                if call.name == "ask_user":
                    answer = yield AskUser(
                        question=call.input.get("question", ""),
                        tool_call_id=call.id,
                        options=call.input.get("options"),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": f"User answered: {answer or '(no answer)'}",
                    })
                    continue

                yield ToolStart(name=call.name)
                try:
                    r = execute(call.name, call.input)
                    yield ToolEnd(name=call.name, result=r)
                except Exception as e:
                    r = {"error": str(e)}
                    yield ToolEnd(name=call.name, error=str(e))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": json.dumps(r, default=str),
                })

            self._messages.append({"role": "user", "content": tool_results})

    def _wrap_stream(
        self, gen: Generator[str, None, TurnResult],
    ) -> Generator[AgentEvent, str | None, TurnResult]:
        """Wrap a provider's str-yielding generator into AgentEvent yields."""
        try:
            while True:
                yield TextDelta(next(gen))
        except StopIteration as e:
            return e.value

    def reset(self):
        self._messages.clear()
