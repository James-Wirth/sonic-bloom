"""Apple Music REST API client for catalog search."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import jwt

_SEARCH_URL = "https://api.music.apple.com/v1/catalog/{storefront}/search"
_GET_URL = "https://api.music.apple.com/v1/catalog/{storefront}/songs/{id}"


class CatalogClient:
    """Apple Music catalog API client with JWT auth."""

    def __init__(self, key_id: str, team_id: str, key_path: Path, storefront: str = "us"):
        self._key_id = key_id
        self._team_id = team_id
        self._key_path = key_path
        self._storefront = storefront
        self._token: str | None = None
        self._token_expiry: float = 0
        self._client = httpx.Client(timeout=10)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        url = _SEARCH_URL.format(storefront=self._storefront)
        resp = self._client.get(
            url,
            headers=self._auth_headers(),
            params={"term": query, "types": "songs", "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        songs = data.get("results", {}).get("songs", {}).get("data", [])
        return [self._parse_song(s) for s in songs]

    def get_song(self, song_id: str) -> dict | None:
        url = _GET_URL.format(storefront=self._storefront, id=song_id)
        resp = self._client.get(url, headers=self._auth_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        songs = data.get("data", [])
        return self._parse_song(songs[0]) if songs else None

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        private_key = self._key_path.read_text()
        now = int(time.time())
        payload = {
            "iss": self._team_id,
            "iat": now,
            "exp": now + 15777000,
        }
        self._token = jwt.encode(
            payload, private_key, algorithm="ES256",
            headers={"kid": self._key_id},
        )
        self._token_expiry = now + 15777000 - 60
        return self._token

    @staticmethod
    def _parse_song(song: dict) -> dict:
        attrs = song.get("attributes", {})
        return {
            "store_id": song.get("id", ""),
            "name": attrs.get("name", ""),
            "artist": attrs.get("artistName", ""),
            "album": attrs.get("albumName", ""),
            "duration_ms": attrs.get("durationInMillis", 0),
            "genre": (attrs.get("genreNames") or [""])[0],
            "url": attrs.get("url", ""),
        }
