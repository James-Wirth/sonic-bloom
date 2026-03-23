"""SOUL.md preference learning."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sonic_bloom.config import CONFIG_DIR

SOUL_FILE = CONFIG_DIR / "SOUL.md"

SOUL_TEMPLATE = """\
# Soul

## Favorite Genres

## Favorite Artists

## Listening Patterns

## Dislikes

## Notes
"""

CONSOLIDATION_PROMPT = """\
You maintain a user preference file for a music assistant. Below is the current \
file and a log of recent interactions. Update the file by incorporating any new \
observations about the user's music tastes.

Rules:
- Append new observations to the appropriate section.
- Remove an entry only if the new interactions directly contradict it.
- Keep the file concise -- aim for under 2000 tokens.
- Preserve the markdown section structure exactly.
- Return ONLY the updated file content, no commentary.

Current file:
---
{current}
---

Recent interactions:
---
{interactions}
---
"""


class SoulManager:
    """Reads and writes ~/.sonic-bloom/SOUL.md, the user preference file."""

    def __init__(self, path: Path = SOUL_FILE):
        self._path = path

    def read(self) -> str | None:
        if not self._path.exists():
            return None
        content = self._path.read_text().strip()
        return content or None

    def update(self, interactions: str, complete: Callable[[list[dict], str | None], str]):
        """Consolidate new observations into SOUL.md.

        Args:
            interactions: Newline-separated log of recent interactions.
            complete: A callable(messages, system) -> str for text completion.
        """
        current = self.read() or SOUL_TEMPLATE
        prompt = CONSOLIDATION_PROMPT.format(current=current, interactions=interactions)
        updated = complete([{"role": "user", "content": prompt}], None)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(updated.strip() + "\n")
