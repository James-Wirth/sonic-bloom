"""Playback control tools."""

from __future__ import annotations

from sonic_bloom.bridge import get_music
from sonic_bloom.tools import tool, slim_track


@tool(description="Toggle play/pause on Music.app.")
def play_pause() -> dict:
    new_state = get_music().playpause()
    return {"state": new_state}


@tool(description="Pause playback.")
def pause() -> dict:
    get_music().pause()
    return {"status": "paused"}


@tool(description="Skip to the next track.")
def next_track() -> dict:
    get_music().next_track()
    track = get_music().current_track()
    if track:
        return {"status": "skipped", "now_playing": slim_track(track)}
    return {"status": "skipped"}


@tool(description="Go back to the previous track.")
def previous_track() -> dict:
    get_music().previous_track()
    track = get_music().current_track()
    if track:
        return {"status": "previous", "now_playing": slim_track(track)}
    return {"status": "previous"}


@tool(
    description="Set the playback volume (0-100).",
    params={"volume": {"type": "integer", "description": "Volume level, 0-100."}},
    required=["volume"],
)
def set_volume(volume: int) -> dict:
    get_music().set_volume(volume)
    return {"volume": max(0, min(100, volume))}


@tool(
    description="Enable or disable shuffle.",
    params={"enabled": {"type": "boolean", "description": "True to enable shuffle."}},
    required=["enabled"],
)
def set_shuffle(enabled: bool) -> dict:
    get_music().set_shuffle(enabled)
    return {"shuffle": enabled}


@tool(
    description="Set repeat mode: 'off', 'one', or 'all'.",
    params={"mode": {"type": "string", "enum": ["off", "one", "all"], "description": "Repeat mode."}},
    required=["mode"],
)
def set_repeat(mode: str) -> dict:
    get_music().set_repeat(mode)
    return {"repeat": mode}


@tool(
    description="Play a specific track by its persistent ID (from search results).",
    params={"persistent_id": {"type": "string", "description": "The track's persistent ID."}},
    required=["persistent_id"],
)
def play_track(persistent_id: str) -> dict:
    get_music().play_track(persistent_id)
    track = get_music().current_track()
    if track:
        return {"status": "playing", "now_playing": slim_track(track)}
    return {"status": "playing"}
