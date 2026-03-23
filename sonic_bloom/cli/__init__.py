"""Terminal interface for Sonic Bloom."""

from __future__ import annotations

import queue

from rich.console import Console

from sonic_bloom.agent import MusicAgent
from sonic_bloom.bridge.events import MusicEvent
from sonic_bloom.cli.commands import handle_command
from sonic_bloom.cli.display import stream_response, print_status
from sonic_bloom.history import record_play

HELP_TEXT = """\

  [bold]Sonic Bloom[/] -- AI music assistant for Apple Music

  [dim]Playback[/]
    [bold cyan]/play[/]     resume          [bold cyan]/pause[/]    pause
    [bold cyan]/next[/]     next track      [bold cyan]/prev[/]     previous track
    [bold cyan]/status[/]   now playing

  [dim]Settings[/]
    [bold cyan]/volume[/]   [dim]<0-100>[/]        [bold cyan]/shuffle[/]  [dim][on|off][/]
    [bold cyan]/repeat[/]   [dim][off|one|all][/]

  [dim]Info[/]
    [bold cyan]/history[/]  [dim][count][/]        [bold cyan]/search[/]   [dim]<query>[/]
    [bold cyan]/playlist[/] [dim][name][/]

  [dim]General[/]
    [bold cyan]/help[/]    show this message
    [bold cyan]quit[/]     exit [dim](also: exit, q, ctrl-c)[/]

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
            if user_input.lower() in ("help", "/help"):
                self.console.print(HELP_TEXT)
                continue
            if user_input.startswith("/"):
                handle_command(self.console, user_input)
                self.console.print()
                continue

            self.console.print()
            try:
                response_text, _, playback_track = stream_response(self.console, self.agent, user_input)
            except Exception as e:
                self.console.print(f"  [red]Error: {e}[/]")
                self.console.print()
                continue
            self.console.print()
            if playback_track:
                record_play(playback_track)
                print_status(self.console, track_data=playback_track)
                self.console.print()

            self.interaction_count += 1
            self.interaction_log.append(f"User: {user_input}")
            if response_text:
                self.interaction_log.append(f"Assistant: {response_text}")

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
