"""Cell - The atomic unit of terminal rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Cell:
    """A single character cell in the terminal buffer.

    Represents one character position with associated styling.
    Uses slots for memory efficiency (terminal buffers can be large).
    """

    char: str = " "
    fg: tuple[int, int, int] | None = None  # RGB TrueColor foreground
    bg: tuple[int, int, int] | None = None  # RGB TrueColor background
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
