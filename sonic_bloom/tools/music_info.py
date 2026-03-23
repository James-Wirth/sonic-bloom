"""Player state and library query tools."""

from __future__ import annotations

from sonic_bloom.bridge import get_music
from sonic_bloom.history import recent_plays
from sonic_bloom.tools import tool, slim_track


@tool(description="Get the currently playing track.")
def get_current_track() -> dict:
    track = get_music().current_track()
    if track:
        return slim_track(track)
    return {"status": "nothing playing"}


@tool(description="Get the full player state: track, volume, shuffle, repeat.")
def get_player_state() -> dict:
    state = get_music().player_state()
    result = {
        "state": state.state,
        "volume": state.volume,
        "shuffle": state.shuffle,
        "repeat": state.repeat,
    }
    if state.current_track:
        result["current_track"] = slim_track(state.current_track)
    return result


@tool(description="Get library statistics: track count, total hours.")
def get_library_stats() -> dict:
    return get_music().get_library_stats()


@tool(
    description="Get recently played tracks.",
    params={"limit": {"type": "integer", "description": "Max tracks to return (default 10)."}},
)
def recently_played(limit: int = 10) -> dict:
    tracks = get_music().recently_played(limit=limit)
    if tracks:
        return {"tracks": [slim_track(t) for t in tracks]}
    history = recent_plays(limit=limit)
    if history:
        return {"tracks": history, "source": "app_history"}
    return {"tracks": []}
