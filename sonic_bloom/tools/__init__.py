"""Tool registry stub."""

from typing import Any

TOOLS: list[dict] = []
HANDLERS: dict[str, Any] = {}


def get_tools() -> list[dict]:
    return TOOLS


def execute(name: str, args: dict) -> Any:
    handler = HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(**args)
