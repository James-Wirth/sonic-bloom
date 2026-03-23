"""Interactive arrow-key selection widget."""

from __future__ import annotations

import sys
import termios
import tty

from rich.console import Console


def read_key() -> str:
    """Read a single keypress. Returns 'up', 'down', 'enter', or the character."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def select(console: Console, question: str, options: list[str]) -> str:
    """Show an interactive menu and return the selected option."""
    console.print(f"\n  [bold]{question}[/]")
    selected = 0
    n = len(options)

    def _draw():
        for i, opt in enumerate(options):
            if i == selected:
                console.print(f"    [bold cyan]> {opt}[/]")
            else:
                console.print(f"      [dim]{opt}[/]")

    _draw()
    while True:
        try:
            key = read_key()
        except KeyboardInterrupt:
            return options[0]
        moved = False
        if key == "up" and selected > 0:
            selected -= 1
            moved = True
        elif key == "down" and selected < n - 1:
            selected += 1
            moved = True
        elif key == "enter":
            break
        if moved:
            sys.stdout.write(f"\033[{n}A\033[J")
            sys.stdout.flush()
            _draw()

    sys.stdout.write(f"\033[{n}A\033[J")
    sys.stdout.flush()
    console.print(f"    [bold cyan]> {options[selected]}[/]")
    console.print()
    return options[selected]
