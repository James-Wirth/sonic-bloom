"""Playlist tools."""

from __future__ import annotations

from sonic_bloom.bridge import get_music
from sonic_bloom.tools import tool, slim_track


@tool(description="List all user playlists.")
def list_playlists() -> dict:
    playlists = get_music().list_playlists()
    return {
        "playlists": [
            {"name": p.name, "track_count": p.track_count}
            for p in playlists
        ]
    }


@tool(
    description="Get tracks in a playlist.",
    params={
        "playlist_name": {"type": "string", "description": "Name of the playlist."},
        "limit": {"type": "integer", "description": "Max tracks to return (default 25)."},
    },
    required=["playlist_name"],
)
def get_playlist_tracks(playlist_name: str, limit: int = 25) -> dict:
    tracks = get_music().get_playlist_tracks(playlist_name, limit=limit)
    return {"playlist": playlist_name, "tracks": [slim_track(t) for t in tracks]}


@tool(
    description="Play a playlist by name.",
    params={"playlist_name": {"type": "string", "description": "Name of the playlist to play."}},
    required=["playlist_name"],
)
def play_playlist(playlist_name: str) -> dict:
    get_music().play_playlist(playlist_name)
    track = get_music().current_track()
    if track:
        return {"status": "playing", "playlist": playlist_name, "now_playing": slim_track(track)}
    return {"status": "playing", "playlist": playlist_name}
