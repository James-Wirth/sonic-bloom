"""Application lifecycle and dependency wiring."""

from __future__ import annotations

from rich.console import Console

from sonic_bloom.config import Config
from sonic_bloom.providers import make_provider


class SonicBloom:
    def __init__(self):
        self.console = Console()
        self.config = Config.load()

    def run(self):
        provider = make_provider(self.config)
        self.console.print(f"\n  [dim]Provider: {self.config.provider} ({self.config.model})[/]\n")
        from sonic_bloom.agent import MusicAgent
        agent = MusicAgent(provider=provider)
        self.console.print("  [green]Agent initialized successfully.[/]\n")
