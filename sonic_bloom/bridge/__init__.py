"""Apple Music bridge — lazy initialization."""

from __future__ import annotations

from sonic_bloom.bridge.scripting_bridge import MusicApp

_music: MusicApp | None = None


def get_music() -> MusicApp:
    """Get the MusicApp singleton, creating it on first call."""
    global _music
    if _music is None:
        _music = MusicApp()
    return _music
