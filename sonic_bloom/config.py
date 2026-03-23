"""Configuration loading from ~/.sonic-bloom/config.toml with env var overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".sonic-bloom"
CONFIG_FILE = CONFIG_DIR / "config.toml"

PROVIDER_DEFAULTS = {
    "anthropic": {"model": "claude-haiku-4-5-20251001"},
    "openai": {"model": "gpt-4o-mini"},
    "ollama": {"model": "llama3.1", "base_url": "http://localhost:11434/v1"},
}

_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@dataclass(frozen=True, slots=True)
class Config:
    """Application configuration with multi-provider support."""

    provider: str = "anthropic"
    model: str = "claude-haiku-4-5-20251001"
    api_key: str | None = None
    base_url: str | None = None
    apple_music_key_id: str | None = None
    apple_music_team_id: str | None = None
    apple_music_key_path: Path | None = None
    storefront: str = "us"

    @classmethod
    def load(cls) -> Config:
        file_vals: dict = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                file_vals = tomllib.load(f)

        provider = os.environ.get("SONIC_BLOOM_PROVIDER") or file_vals.get("provider", "anthropic")
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        provider_section = file_vals.get(provider, {})
        apple_section = file_vals.get("apple_music", {})

        env_key = _API_KEY_ENV.get(provider)
        api_key = (
            (os.environ.get(env_key) if env_key else None)
            or provider_section.get("api_key")
            or file_vals.get("api_key")
        )

        model = (
            os.environ.get("SONIC_BLOOM_MODEL")
            or provider_section.get("model")
            or file_vals.get("model")
            or defaults.get("model", "claude-haiku-4-5-20251001")
        )

        base_url = provider_section.get("base_url") or defaults.get("base_url")

        key_path_raw = (
            os.environ.get("APPLE_MUSIC_KEY_PATH")
            or apple_section.get("key_path")
        )

        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            apple_music_key_id=(
                os.environ.get("APPLE_MUSIC_KEY_ID") or apple_section.get("key_id")
            ),
            apple_music_team_id=(
                os.environ.get("APPLE_MUSIC_TEAM_ID") or apple_section.get("team_id")
            ),
            apple_music_key_path=Path(key_path_raw).expanduser() if key_path_raw else None,
            storefront=(
                os.environ.get("APPLE_MUSIC_STOREFRONT") or apple_section.get("storefront", "us")
            ),
        )

    @property
    def catalog_available(self) -> bool:
        return bool(
            self.apple_music_key_id
            and self.apple_music_team_id
            and self.apple_music_key_path
            and self.apple_music_key_path.exists()
        )
