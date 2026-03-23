"""Persistent play history stored in ~/.sonic-bloom/history.json."""

from __future__ import annotations

import json
from datetime import datetime

from sonic_bloom.config import CONFIG_DIR

HISTORY_FILE = CONFIG_DIR / "history.json"
MAX_ENTRIES = 200


def record_play(track_data: dict):
    """Append a played track to history."""
    name = track_data.get("name")
    if not name:
        return
    entries = _load()
    entries.append({
        "name": name,
        "artist": track_data.get("artist", ""),
        "album": track_data.get("album", ""),
        "played_at": datetime.now().isoformat(),
    })
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(entries, indent=2))


def recent_plays(limit: int = 10) -> list[dict]:
    """Return the most recent plays, newest first."""
    entries = _load()
    return list(reversed(entries[-limit:]))


def _load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
