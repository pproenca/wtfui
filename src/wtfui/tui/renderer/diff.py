from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wtfui.tui.renderer import ansi
from wtfui.tui.renderer.cell import Cell

if TYPE_CHECKING:
    from wtfui.tui.renderer.buffer import Buffer


@dataclass
class DiffResult:
    changes: list[tuple[int, int]] = field(default_factory=list)
    ansi_output: str = ""


def diff_buffers(old: Buffer, new: Buffer) -> DiffResult:
    changes: list[tuple[int, int]] = []
    output_parts: list[str] = []

    last_fg: tuple[int, int, int] | None = None
    last_bg: tuple[int, int, int] | None = None
    last_bold: bool = False
    last_dim: bool = False
    last_italic: bool = False
    last_underline: bool = False

    cursor_x: int = -1
    cursor_y: int = -1

    new_width = new.width
    changes_append = changes.append
    output_append = output_parts.append
    cursor_move = ansi.cursor_move

    old_width = old.width
    old_height = old.height

    old_cells = old._cells
    new_cells = new._cells

    blank_cell = Cell()

    idx = 0
    new_height = new.height
    for y in range(new_height):
        for x in range(new_width):
            new_cell = new_cells[idx]
            idx += 1

            if y < old_height and x < old_width:
                old_idx = y * old_width + x
                old_cell = old_cells[old_idx]
            else:
                old_cell = blank_cell

            if old_cell != new_cell:
                changes_append((x, y))

                if cursor_x != x or cursor_y != y:
                    output_append(cursor_move(x, y))

                style_parts = _build_style_sequence(
                    new_cell, last_fg, last_bg, last_bold, last_dim, last_italic, last_underline
                )
                if style_parts:
                    output_append(style_parts)
                    last_fg = new_cell.fg
                    last_bg = new_cell.bg
                    last_bold = new_cell.bold
                    last_dim = new_cell.dim
                    last_italic = new_cell.italic
                    last_underline = new_cell.underline

                output_append(new_cell.char)

                cursor_x = x + 1
                cursor_y = y

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
    parts: list[str] = []

    need_reset = (
        (last_bold and not cell.bold)
        or (last_dim and not cell.dim)
        or (last_italic and not cell.italic)
        or (last_underline and not cell.underline)
    )

    if need_reset:
        parts.append(ansi.reset_style())

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
