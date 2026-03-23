"""Slash command handlers for the Sonic Bloom CLI."""

from __future__ import annotations

from typing import Callable

from rich.console import Console
from rich.table import Table
from rich.padding import Padding

from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.scripting_bridge import MusicAppError
from sonic_bloom.cli.display import print_status
from sonic_bloom.history import recent_plays

CommandHandler = Callable[[Console, str], None]
COMMANDS: dict[str, CommandHandler] = {}


def command(name: str):
    """Register a slash command handler."""
    def decorator(fn: CommandHandler) -> CommandHandler:
        COMMANDS[name] = fn
        return fn
    return decorator


def handle_command(console: Console, raw_input: str):
    """Parse and dispatch a slash command. raw_input includes the leading /."""
    parts = raw_input[1:].split(None, 1)
    name = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(name)
    if handler is None:
        console.print(f"  [red]Unknown command: /{name}[/]  —  type [bold cyan]/help[/] for available commands")
        return

    try:
        handler(console, args)
    except MusicAppError as e:
        console.print(f"  [red]{e}[/]")


# --- Playback commands ---

@command("play")
def _play(console: Console, _args: str):
    m = get_music()
    state = m.player_state().state
    if state == "playing":
        console.print("  [dim]Already playing[/]")
        return
    m.playpause()
    console.print("  [dim]▶ playing[/]")


@command("pause")
def _pause(console: Console, _args: str):
    m = get_music()
    m.pause()
    console.print("  [dim]⏸ paused[/]")


@command("next")
def _next(console: Console, _args: str):
    get_music().next_track()
    track = get_music().current_track()
    if track:
        console.print(f"  [dim]⏭ {track.name} — {track.artist}[/]")


@command("prev")
def _prev(console: Console, _args: str):
    get_music().previous_track()
    track = get_music().current_track()
    if track:
        console.print(f"  [dim]⏮ {track.name} — {track.artist}[/]")


@command("status")
def _status(console: Console, _args: str):
    print_status(console)


# --- Settings commands ---

@command("volume")
def _volume(console: Console, args: str):
    if not args:
        vol = get_music().player_state().volume
        console.print(f"  [dim]Volume: {vol}[/]")
        return
    try:
        level = int(args)
    except ValueError:
        console.print("  [red]Usage: /volume <0-100>[/]")
        return
    if not 0 <= level <= 100:
        console.print("  [red]Volume must be 0-100[/]")
        return
    get_music().set_volume(level)
    console.print(f"  [dim]Volume set to {level}[/]")


@command("shuffle")
def _shuffle(console: Console, args: str):
    m = get_music()
    if not args:
        current = m.player_state().shuffle
        m.set_shuffle(not current)
        console.print(f"  [dim]Shuffle {'on' if not current else 'off'}[/]")
        return
    if args.lower() not in ("on", "off"):
        console.print("  [red]Usage: /shuffle [on|off][/]")
        return
    enabled = args.lower() == "on"
    m.set_shuffle(enabled)
    console.print(f"  [dim]Shuffle {'on' if enabled else 'off'}[/]")


@command("repeat")
def _repeat(console: Console, args: str):
    if not args:
        mode = get_music().player_state().repeat
        console.print(f"  [dim]Repeat: {mode}[/]")
        return
    if args.lower() not in ("off", "one", "all"):
        console.print("  [red]Usage: /repeat [off|one|all][/]")
        return
    get_music().set_repeat(args.lower())
    console.print(f"  [dim]Repeat: {args.lower()}[/]")


# --- Info commands ---

@command("history")
def _history(console: Console, args: str):
    limit = 10
    if args:
        try:
            limit = int(args)
        except ValueError:
            console.print("  [red]Usage: /history [count][/]")
            return

    entries = recent_plays(limit)
    if not entries:
        console.print("  [dim]No play history yet[/]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(style="dim")
    for entry in entries:
        table.add_row(entry["name"], entry.get("artist", ""))
    console.print(Padding(table, (0, 0, 0, 2)))


@command("playlist")
def _playlist(console: Console, args: str):
    if not args:
        playlists = get_music().list_playlists()
        if not playlists:
            console.print("  [dim]No playlists found[/]")
            return
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(style="dim")
        for p in playlists:
            table.add_row(p.name, f"{p.track_count} tracks")
        console.print(Padding(table, (0, 0, 0, 2)))
        return

    get_music().play_playlist(args)
    track = get_music().current_track()
    if track:
        console.print(f"  [dim]▶ Playing playlist: {args}[/]")
        print_status(console)
    else:
        console.print(f"  [dim]▶ Playing playlist: {args}[/]")


@command("search")
def _search(console: Console, args: str):
    if not args:
        console.print("  [red]Usage: /search <query>[/]")
        return
    tracks = get_music().search_library(args, limit=10)
    if not tracks:
        console.print(f"  [dim]No results for: {args}[/]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_column(style="dim")
    for t in tracks:
        table.add_row(t.name, t.artist, t.album)
    console.print(Padding(table, (0, 0, 0, 2)))
