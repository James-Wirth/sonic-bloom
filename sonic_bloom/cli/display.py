"""Streaming response display and status formatting."""

from __future__ import annotations

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from sonic_bloom.agent import AgentEvent, AskUser, MusicAgent, TextDelta, ToolEnd, ToolStart
from sonic_bloom.bridge import get_music
from sonic_bloom.bridge.scripting_bridge import MusicAppError
from sonic_bloom.cli.selection import select

_TOOL_LABELS = {
    "search_library": "Searching library",
    "search_catalog": "Searching catalog",
    "search_itunes": "Searching iTunes",
    "search_and_play": "Searching and playing",
    "play_from_itunes": "Playing from iTunes",
    "play_playlist": "Playing playlist",
    "get_current_track": "Checking current track",
    "get_player_state": "Getting player state",
    "get_library_stats": "Getting library stats",
    "recently_played": "Checking recently played",
    "play_track": "Playing track",
    "list_playlists": "Listing playlists",
    "get_playlist_tracks": "Getting playlist tracks",
}

PLAYBACK_TOOLS = {
    "play_pause", "pause", "next_track", "previous_track",
    "play_track", "search_and_play", "play_from_itunes",
    "play_playlist", "set_volume", "set_shuffle", "set_repeat",
}


def tool_label(name: str) -> str:
    return _TOOL_LABELS.get(name, name.replace("_", " ").title())


def _extract_track(tool_name: str, result: dict | None) -> dict | None:
    """Extract track info dict from a playback tool result, if present."""
    if not result or tool_name not in PLAYBACK_TOOLS:
        return None
    return result.get("track") or result.get("now_playing")


def stream_response(console: Console, agent: MusicAgent, user_input: str) -> tuple[str, set[str], dict | None]:
    """Stream agent response to the console. Returns (response_text, tools_used, playback_track)."""
    accumulated = ""
    tools_used: set[str] = set()
    playback_track: dict | None = None
    gen = agent.chat(user_input)
    event: AgentEvent | None = next(gen, None)

    with Live(
        Spinner("dots", text="[dim]Thinking...[/]"),
        console=console,
        refresh_per_second=12,
        transient=True,
    ) as live:
        while event is not None:
            match event:
                case TextDelta(text=text):
                    accumulated += text
                    if tools_used:
                        live.update(Markdown(accumulated))
                    else:
                        live.update(Text(accumulated, style="dim italic"))
                case ToolStart(name=name):
                    tools_used.add(name)
                    label = tool_label(name)
                    if accumulated:
                        console.print(Text(accumulated.strip(), style="dim italic"))
                        accumulated = ""
                    live.update(Spinner("dots", text=f"[dim]{label}...[/]"))
                case ToolEnd(name=name, result=result):
                    playback_track = _extract_track(name, result) or playback_track
                    live.update(Spinner("dots", text="[dim]Thinking...[/]"))
                case AskUser(question=question, options=options):
                    live.stop()
                    if options:
                        answer = select(console, question, options)
                    else:
                        console.print(f"\n  [bold]{question}[/]")
                        try:
                            answer = console.input("  [bold cyan]>[/] ").strip()
                        except (KeyboardInterrupt, EOFError):
                            answer = ""
                        console.print()
                    live.start()
                    live.update(Spinner("dots", text="[dim]Thinking...[/]"))
                    event = gen.send(answer)
                    continue
            event = next(gen, None)

    if accumulated:
        if tools_used:
            console.print()
        console.print(Markdown(accumulated))
    return accumulated, tools_used, playback_track


def print_status(console: Console, track_data: dict | None = None):
    """Print current player status. Uses track_data if provided, else queries Music.app."""
    try:
        state = get_music().player_state()
        if track_data:
            name = track_data.get("name", "Unknown")
            artist = track_data.get("artist", "Unknown")
            album = track_data.get("album", "")
        elif state.current_track:
            name = state.current_track.name
            artist = state.current_track.artist
            album = state.current_track.album
        else:
            console.print("  [dim]No track playing[/]")
            return
        icon = ">" if state.state == "playing" else "||" if state.state == "paused" else "[]"
        console.print(f"  {icon} [bold]{name}[/] -- {artist} [dim]({album})[/]")
        details = [
            f"vol {state.volume}",
            f"shuffle {'on' if state.shuffle else 'off'}",
            f"repeat {state.repeat}",
        ]
        console.print(f"    [dim]{' . '.join(details)}[/]")
    except MusicAppError as e:
        console.print(f"  [red]{e}[/]")
