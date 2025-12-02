# src/flow/renderer/console/diff.py
"""Differential painting - minimize terminal writes by comparing buffers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from flow.renderer.console import ansi

if TYPE_CHECKING:
    from flow.renderer.console.buffer import Buffer
    from flow.renderer.console.cell import Cell


@dataclass
class DiffResult:
    """Result of comparing two buffers.

    Attributes:
        changes: List of (x, y) positions that changed.
        ansi_output: Optimized ANSI string to apply changes.
    """

    changes: list[tuple[int, int]] = field(default_factory=list)
    ansi_output: str = ""


def diff_buffers(old: Buffer, new: Buffer) -> DiffResult:
    """Compare two buffers and generate minimal ANSI output.

    This is the core of the differential painting engine.
    Only cells that differ between old and new are written.

    Args:
        old: The current screen state (Buffer A).
        new: The desired next frame (Buffer B).

    Returns:
        DiffResult with change positions and ANSI string.
    """
    changes: list[tuple[int, int]] = []
    output_parts: list[str] = []

    # Track last style to avoid redundant escape sequences
    last_fg: tuple[int, int, int] | None = None
    last_bg: tuple[int, int, int] | None = None
    last_bold: bool = False
    last_dim: bool = False
    last_italic: bool = False
    last_underline: bool = False

    # Track cursor position to minimize cursor movements
    cursor_x: int = -1
    cursor_y: int = -1

    for y in range(new.height):
        for x in range(new.width):
            old_cell = old.get(x, y)
            new_cell = new.get(x, y)

            if old_cell != new_cell:
                changes.append((x, y))

                # Move cursor if not at expected position
                if cursor_x != x or cursor_y != y:
                    output_parts.append(ansi.cursor_move(x, y))

                # Apply style changes
                style_parts = _build_style_sequence(
                    new_cell, last_fg, last_bg, last_bold, last_dim, last_italic, last_underline
                )
                if style_parts:
                    output_parts.append(style_parts)
                    last_fg = new_cell.fg
                    last_bg = new_cell.bg
                    last_bold = new_cell.bold
                    last_dim = new_cell.dim
                    last_italic = new_cell.italic
                    last_underline = new_cell.underline

                # Write character
                output_parts.append(new_cell.char)

                # Update cursor position (moves right after writing)
                cursor_x = x + 1
                cursor_y = y

    # Reset style at end if we made any changes
    if output_parts:
        output_parts.append(ansi.reset_style())

    return DiffResult(
        changes=changes,
        ansi_output="".join(output_parts),
    )


def _build_style_sequence(
    cell: Cell,
    last_fg: tuple[int, int, int] | None,
    last_bg: tuple[int, int, int] | None,
    last_bold: bool,
    last_dim: bool,
    last_italic: bool,
    last_underline: bool,
) -> str:
    """Build ANSI style sequence, only including changed attributes."""
    parts: list[str] = []

    # Check if we need to reset (style attributes going from on to off)
    need_reset = (
        (last_bold and not cell.bold)
        or (last_dim and not cell.dim)
        or (last_italic and not cell.italic)
        or (last_underline and not cell.underline)
    )

    if need_reset:
        parts.append(ansi.reset_style())
        # After reset, we need to re-apply all current styles
        if cell.fg:
            parts.append(ansi.set_fg_rgb(*cell.fg))
        if cell.bg:
            parts.append(ansi.set_bg_rgb(*cell.bg))
        if cell.bold:
            parts.append(ansi.set_bold())
        if cell.dim:
            parts.append(ansi.set_dim())
        if cell.italic:
            parts.append(ansi.set_italic())
        if cell.underline:
            parts.append(ansi.set_underline())
    else:
        # Only emit changed attributes
        if cell.fg != last_fg and cell.fg:
            parts.append(ansi.set_fg_rgb(*cell.fg))
        if cell.bg != last_bg and cell.bg:
            parts.append(ansi.set_bg_rgb(*cell.bg))
        if cell.bold and not last_bold:
            parts.append(ansi.set_bold())
        if cell.dim and not last_dim:
            parts.append(ansi.set_dim())
        if cell.italic and not last_italic:
            parts.append(ansi.set_italic())
        if cell.underline and not last_underline:
            parts.append(ansi.set_underline())

    return "".join(parts)
