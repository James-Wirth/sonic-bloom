"""Library, catalog, and iTunes search tools."""

from __future__ import annotations

import httpx

from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.scripting_bridge import play_store_track
from sonic_bloom.config import Config
from sonic_bloom.tools import tool, slim_track


def _get_catalog():
    """Lazily create a catalog client if credentials are configured."""
    config = Config.load()
    if not config.catalog_available:
        return None
    from sonic_bloom.bridge.catalog import CatalogClient
    return CatalogClient(
        key_id=config.apple_music_key_id,
        team_id=config.apple_music_team_id,
        key_path=config.apple_music_key_path,
        storefront=config.storefront,
    )


def _itunes_search(query: str, limit: int = 5) -> list[dict]:
    """Search the iTunes Search API (no auth required)."""
    resp = httpx.get(
        "https://itunes.apple.com/search",
        params={"term": query, "media": "music", "entity": "song", "limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    results = []
    for item in resp.json().get("results", []):
        results.append({
            "store_id": str(item.get("trackId", "")),
            "name": item.get("trackName", ""),
            "artist": item.get("artistName", ""),
            "album": item.get("collectionName", ""),
            "duration_ms": item.get("trackTimeMillis", 0),
            "genre": item.get("primaryGenreName", ""),
        })
    return results


@tool(
    description="Search the user's local Music.app library.",
    params={
        "query": {"type": "string", "description": "Search query (song, artist, album)."},
        "limit": {"type": "integer", "description": "Max results (default 10)."},
    },
    required=["query"],
)
def search_library(query: str, limit: int = 10) -> dict:
    tracks = get_music().search_library(query, limit=limit)
    return {"results": [slim_track(t) for t in tracks], "source": "library"}


@tool(
    description="Search the Apple Music catalog (requires API credentials).",
    params={
        "query": {"type": "string", "description": "Search query."},
        "limit": {"type": "integer", "description": "Max results (default 5)."},
    },
    required=["query"],
)
def search_catalog(query: str, limit: int = 5) -> dict:
    catalog = _get_catalog()
    if catalog is None:
        return {"error": "Apple Music catalog not configured"}
    results = catalog.search(query, limit=limit)
    return {"results": results, "source": "catalog"}


@tool(
    description="Search iTunes (no auth needed, broader catalog).",
    params={
        "query": {"type": "string", "description": "Search query."},
        "limit": {"type": "integer", "description": "Max results (default 5)."},
    },
    required=["query"],
)
def search_itunes(query: str, limit: int = 5) -> dict:
    results = _itunes_search(query, limit=limit)
    return {"results": results, "source": "itunes"}


@tool(
    description=(
        "Search and play a song. Tries: library first, then catalog (if configured), "
        "then iTunes. Use for direct 'play X' requests."
    ),
    params={
        "query": {"type": "string", "description": "What to search for (song, artist, etc)."},
    },
    required=["query"],
)
def search_and_play(query: str) -> dict:
    # Try library first
    tracks = get_music().search_library(query, limit=1)
    if tracks:
        get_music().play_track(tracks[0].persistent_id)
        return {"status": "playing", "source": "library", "track": slim_track(tracks[0])}

    # Try catalog
    catalog = _get_catalog()
    if catalog:
        results = catalog.search(query, limit=1)
        if results:
            play_store_track(results[0]["store_id"])
            return {"status": "playing", "source": "catalog", "track": results[0]}

    # Fall back to iTunes
    results = _itunes_search(query, limit=1)
    if results:
        play_store_track(results[0]["store_id"])
        return {"status": "playing", "source": "itunes", "track": results[0]}

    return {"error": f"No results found for: {query}"}


@tool(
    description="Play a track from the iTunes/Apple Music store by its store ID.",
    params={
        "store_id": {"type": "string", "description": "The iTunes/catalog store ID."},
        "name": {"type": "string", "description": "Track name (for display)."},
        "artist": {"type": "string", "description": "Artist name (for display)."},
        "album": {"type": "string", "description": "Album name (for display)."},
    },
    required=["store_id"],
)
def play_from_itunes(store_id: str, name: str = "", artist: str = "", album: str = "") -> dict:
    play_store_track(store_id)
    track = get_music().current_track()
    if track:
        return {"status": "playing", "track": slim_track(track)}
    return {"status": "playing", "track": {"name": name, "artist": artist, "album": album}}
