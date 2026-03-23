"""Provider protocol and factory for LLM backends."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Protocol

from sonic_bloom.config import Config


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass(slots=True)
class TurnResult:
    content: list[dict]
    tool_calls: list[ToolCall]
    stop_reason: str


class Provider(Protocol):
    def stream_turn(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
    ) -> Generator[str, None, TurnResult]:
        """Stream a turn. Yields text deltas, returns TurnResult."""
        ...

    def simple_completion(self, messages: list[dict], system: str | None = None) -> str:
        """Non-streaming text completion (for soul consolidation, etc.)."""
        ...


def make_provider(config: Config) -> Provider:
    match config.provider:
        case "anthropic":
            from sonic_bloom.providers.anthropic import AnthropicProvider
            return AnthropicProvider(api_key=config.api_key, model=config.model)
        case "openai":
            from sonic_bloom.providers.openai import OpenAIProvider
            return OpenAIProvider(api_key=config.api_key, model=config.model, base_url=config.base_url)
        case "ollama":
            from sonic_bloom.providers.openai import OpenAIProvider
            return OpenAIProvider(
                api_key="ollama",
                model=config.model,
                base_url=config.base_url or "http://localhost:11434/v1",
            )
        case _:
            raise ValueError(f"Unknown provider: {config.provider!r}")
