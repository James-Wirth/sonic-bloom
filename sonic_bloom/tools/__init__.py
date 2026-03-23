"""Decorator-based tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sonic_bloom.bridge.scripting_bridge import Track


@dataclass(frozen=True, slots=True)
class ToolDef:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]


_REGISTRY: dict[str, ToolDef] = {}


def tool(
    description: str,
    params: dict | None = None,
    required: list[str] | None = None,
):
    """Register a function as an agent tool."""
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[fn.__name__] = ToolDef(
            name=fn.__name__,
            description=description,
            parameters={
                "type": "object",
                "properties": params or {},
                "required": required or [],
            },
            handler=fn,
        )
        return fn
    return decorator


def get_tools() -> list[dict]:
    """Return provider-agnostic tool schemas for all registered tools."""
    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in _REGISTRY.values()
    ]


def execute(name: str, args: dict[str, Any]) -> Any:
    td = _REGISTRY.get(name)
    if td is None:
        raise ValueError(f"Unknown tool: {name}")
    return td.handler(**args)


def slim_track(track: Track) -> dict:
    """Minimal track info for LLM consumption."""
    return {
        "name": track.name,
        "artist": track.artist,
        "album": track.album,
        "duration": round(track.duration),
        "persistent_id": track.persistent_id,
    }


def _ask_user_placeholder(**_: Any) -> None:
    raise NotImplementedError("ask_user is handled by the agent, not the registry")


_REGISTRY["ask_user"] = ToolDef(
    name="ask_user",
    description=(
        "Ask the user a clarifying question when you're unsure. "
        "Use when: multiple matches found, ambiguous request, or need a preference. "
        "Do NOT use for straightforward requests — just act. "
        "When providing options, keep them short and specific (no emoji, no numbering)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "A clear, concise question for the user."},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices. Omit for free-text input.",
            },
        },
        "required": ["question"],
    },
    handler=_ask_user_placeholder,
)

# Import tool modules to trigger @tool registration
from sonic_bloom.tools import music_control, music_info, music_search, music_playlists  # noqa: E402, F401
