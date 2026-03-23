"""Application lifecycle and dependency wiring."""

from __future__ import annotations

from rich.console import Console

from sonic_bloom.agent import MusicAgent
from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.events import MusicEventThread
from sonic_bloom.cli import SonicBloomCLI
from sonic_bloom.cli.selection import select
from sonic_bloom.config import CONFIG_DIR, CONFIG_FILE, Config, PROVIDER_DEFAULTS, _API_KEY_ENV
from sonic_bloom.providers import make_provider
from sonic_bloom.soul.manager import SoulManager

SOUL_UPDATE_INTERVAL = 10

BANNER = (
    "  ███████╗ ██████╗ ███╗   ██╗██╗ ██████╗\n"
    "  ██╔════╝██╔═══██╗████╗  ██║██║██╔════╝\n"
    "  ███████╗██║   ██║██╔██╗ ██║██║██║     \n"
    "  ╚════██║██║   ██║██║╚██╗██║██║██║     \n"
    "  ███████║╚██████╔╝██║ ╚████║██║╚██████╗\n"
    "  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝\n"
    "  ██████╗ ██╗      ██████╗  ██████╗ ███╗   ███╗\n"
    "  ██╔══██╗██║     ██╔═══██╗██╔═══██╗████╗ ████║\n"
    "  ██████╔╝██║     ██║   ██║██║   ██║██╔████╔██║\n"
    "  ██╔══██╗██║     ██║   ██║██║   ██║██║╚██╔╝██║\n"
    "  ██████╔╝███████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║\n"
    "  ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝"
)


class SonicBloom:
    def __init__(self):
        self.console = Console()
        self.config = Config.load()
        self.soul = SoulManager()

    def run(self):
        self.console.print()
        self.console.print(f"[bold #5b4a9e]{BANNER}[/]")
        self.console.print("  [dim]AI music assistant for Apple Music[/]")
        self.console.print()

        self._check_music_app()
        soul_content = self.soul.read()

        provider = self._make_provider()
        if not provider:
            return
        agent = MusicAgent(provider=provider, soul_content=soul_content)

        event_thread = MusicEventThread()
        event_thread.start()

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
            if not self._setup():
                return None
        if self.config.provider == "ollama" and not self._check_ollama():
            return None
        try:
            return make_provider(self.config)
        except Exception as e:
            self.console.print(f"  [red]Could not initialize {self.config.provider}: {e}[/]")
            return None

    def _setup(self) -> bool:
        """First-run setup: choose provider and enter API key."""
        self.console.print("  [bold]First-run setup[/]")

        providers = list(PROVIDER_DEFAULTS.keys())
        provider = select(self.console, "Choose a provider:", providers)

        if provider == "ollama":
            self._write_config(provider)
            self.config = Config.load()
            return True

        env_var = _API_KEY_ENV.get(provider, "API_KEY")
        self.console.print(f"  [dim]You can also set [bold]{env_var}[/] instead.[/]\n")
        try:
            key = self.console.input("  API key: ", password=True).strip()
        except (KeyboardInterrupt, EOFError):
            self.console.print()
            return False

        if not key:
            self.console.print("  [red]No API key provided.[/]\n")
            return False

        self._write_config(provider, key)
        self.config = Config.load()
        self.console.print("  [green]Config saved.[/]\n")
        return True

    def _write_config(self, provider: str, api_key: str | None = None):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        lines = [f'provider = "{provider}"']
        if api_key:
            lines.append(f"\n[{provider}]")
            lines.append(f'api_key = "{api_key}"')
        if CONFIG_FILE.exists():
            existing = CONFIG_FILE.read_text()
            if existing.strip():
                lines = [existing.rstrip(), ""] + lines
        CONFIG_FILE.write_text("\n".join(lines) + "\n")

    def _check_ollama(self) -> bool:
        import httpx
        base = self.config.base_url or "http://localhost:11434"
        try:
            httpx.get(f"{base}/api/tags", timeout=3)
            return True
        except httpx.ConnectError:
            self.console.print(f"  [red]Cannot connect to Ollama at {base}.[/]")
            self.console.print("  [dim]Start Ollama with: ollama serve[/]\n")
            return False

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
