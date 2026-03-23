"""Terminal interface for Sonic Bloom."""

from __future__ import annotations

import queue

from rich.console import Console

from sonic_bloom.agent import MusicAgent
from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.events import MusicEvent
from sonic_bloom.bridge.scripting_bridge import MusicAppError
from sonic_bloom.cli.display import stream_response, print_status, PLAYBACK_TOOLS

SHORTCUTS = {
    "p": "play_pause",
    "n": "next_track",
    "b": "previous_track",
    "s": "status",
}

HELP_TEXT = """\

  [bold]Sonic Bloom[/] -- AI music assistant for Apple Music

  [dim]Shortcuts[/]
    [bold cyan]p[/]  play / pause       [bold cyan]n[/]  next track
    [bold cyan]b[/]  previous track     [bold cyan]s[/]  now playing

  [dim]Commands[/]
    [bold cyan]help[/]   show this message
    [bold cyan]quit[/]   exit [dim](also: exit, q, ctrl-c)[/]

  Anything else is sent to the AI assistant.
"""


class SonicBloomCLI:
    def __init__(self, console: Console, agent: MusicAgent, event_queue: queue.Queue[MusicEvent]):
        self.console = console
        self.agent = agent
        self.event_queue = event_queue
        self.interaction_count = 0
        self.interaction_log: list[str] = []

    def loop(self):
        while True:
            self._drain_events()
            try:
                user_input = self.console.input("[bold cyan]>[/] ").strip()
            except (KeyboardInterrupt, EOFError):
                return

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                return
            if user_input.lower() == "help":
                self.console.print(HELP_TEXT)
                continue
            if user_input.lower() in SHORTCUTS:
                self._handle_shortcut(user_input.lower())
                self.console.print()
                continue

            self.console.print()
            response_text, tools_used = stream_response(self.console, self.agent, user_input)
            self.console.print()
            if tools_used & PLAYBACK_TOOLS:
                print_status(self.console)
                self.console.print()

            self.interaction_count += 1
            self.interaction_log.append(f"User: {user_input}")
            if response_text:
                self.interaction_log.append(f"Assistant: {response_text}")

    def _handle_shortcut(self, key: str):
        m = get_music()
        try:
            match key:
                case "p":
                    new_state = m.playpause()
                    icon = ">" if new_state == "playing" else "||"
                    self.console.print(f"  [dim]{icon} {new_state}[/]")
                case "n":
                    m.next_track()
                    track = m.current_track()
                    if track:
                        self.console.print(f"  [dim]>> {track.name} -- {track.artist}[/]")
                case "b":
                    m.previous_track()
                    track = m.current_track()
                    if track:
                        self.console.print(f"  [dim]<< {track.name} -- {track.artist}[/]")
                case "s":
                    print_status(self.console)
        except MusicAppError as e:
            self.console.print(f"  [red]{e}[/]")

    def _drain_events(self):
        last: MusicEvent | None = None
        while True:
            try:
                last = self.event_queue.get_nowait()
            except queue.Empty:
                break
        if last and last.name and last.state == "Playing":
            print_status(self.console)
            self.console.print()
