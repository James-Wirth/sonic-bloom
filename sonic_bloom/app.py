"""Application lifecycle and dependency wiring."""

from __future__ import annotations

from rich.console import Console

from sonic_bloom.agent import MusicAgent
from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.events import MusicEventThread
from sonic_bloom.cli import SonicBloomCLI
from sonic_bloom.config import CONFIG_DIR, Config
from sonic_bloom.providers import make_provider
from sonic_bloom.soul.manager import SoulManager

SOUL_UPDATE_INTERVAL = 10

BANNER = (
    "███████╗ ██████╗ ███╗   ██╗██╗ ██████╗    ██████╗ ██╗      ██████╗  ██████╗ ███╗   ███╗\n"
    "██╔════╝██╔═══██╗████╗  ██║██║██╔════╝    ██╔══██╗██║     ██╔═══██╗██╔═══██╗████╗ ████║\n"
    "███████╗██║   ██║██╔██╗ ██║██║██║         ██████╔╝██║     ██║   ██║██║   ██║██╔████╔██║\n"
    "╚════██║██║   ██║██║╚██╗██║██║██║         ██╔══██╗██║     ██║   ██║██║   ██║██║╚██╔╝██║\n"
    "███████║╚██████╔╝██║ ╚████║██║╚██████╗    ██████╔╝███████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║\n"
    "╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝    ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝"
)


class SonicBloom:
    def __init__(self):
        self.console = Console()
        self.config = Config.load()
        self.soul = SoulManager()

    def run(self):
        self._check_music_app()
        soul_content = self.soul.read()

        provider = self._make_provider()
        if not provider:
            return
        agent = MusicAgent(provider=provider, soul_content=soul_content)

        event_thread = MusicEventThread()
        event_thread.start()

        self.console.print()
        self.console.print(f"[bold #5b4a9e]{BANNER}[/]")
        self.console.print("  [dim]AI music assistant for Apple Music[/]")
        self.console.print()

        cli = SonicBloomCLI(self.console, agent, event_thread.queue)
        try:
            cli.loop()
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._maybe_update_soul(cli, provider, force=True)
            self.console.print("\n  [dim]Goodbye.[/]\n")
            event_thread.stop()

    def _check_music_app(self):
        try:
            m = get_music()
            if not m.is_running:
                self.console.print("  [yellow]Music.app is not running. Starting it...[/]")
                m.activate()
        except Exception:
            self.console.print("  [yellow]Could not check Music.app status.[/]")

    def _make_provider(self):
        if not self.config.api_key and self.config.provider != "ollama":
            self.console.print(f"\n  [bold]No API key configured for {self.config.provider}.[/]")
            self.console.print(f"  Set the appropriate env var or add it to [dim]{CONFIG_DIR / 'config.toml'}[/]\n")
            return None
        try:
            return make_provider(self.config)
        except Exception as e:
            self.console.print(f"  [red]Could not initialize {self.config.provider}: {e}[/]")
            return None

    def _maybe_update_soul(self, cli: SonicBloomCLI, provider, force: bool = False):
        if not cli.interaction_log:
            return
        if not force and cli.interaction_count % SOUL_UPDATE_INTERVAL != 0:
            return
        try:
            self.soul.update(
                "\n".join(cli.interaction_log),
                provider.simple_completion,
            )
            cli.interaction_log.clear()
        except Exception:
            self.console.print("  [dim]Could not update preferences.[/]")
