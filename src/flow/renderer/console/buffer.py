# src/flow/renderer/console/buffer.py
"""Buffer - The terminal framebuffer for double-buffered rendering."""

from __future__ import annotations

from flow.renderer.console.cell import Cell


class Buffer:
    """A 2D grid of Cells representing terminal screen state.

    Used for double-buffering: maintain Buffer A (current screen)
    and Buffer B (next frame), then diff to minimize writes.
    """

    __slots__ = ("_cells", "height", "width")

    def __init__(self, width: int, height: int) -> None:
        """Initialize buffer with given dimensions.

        Args:
            width: Number of columns.
            height: Number of rows.
        """
        self.width = width
        self.height = height
        # Pre-allocate grid as flat list for cache efficiency
        self._cells: list[Cell] = [Cell() for _ in range(width * height)]

    def _index(self, x: int, y: int) -> int | None:
        """Convert (x, y) to flat index, or None if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return y * self.width + x
        return None

    def get(self, x: int, y: int) -> Cell:
        """Get cell at (x, y). Returns default Cell if out of bounds."""
        idx = self._index(x, y)
        if idx is not None:
            return self._cells[idx]
        return Cell()

    def set(self, x: int, y: int, cell: Cell) -> None:
        """Set cell at (x, y). Silently ignores out of bounds."""
        idx = self._index(x, y)
        if idx is not None:
            self._cells[idx] = cell

    def clear(self) -> None:
        """Reset all cells to default (empty space)."""
        self._cells = [Cell() for _ in range(self.width * self.height)]

    def write_text(
        self,
        x: int,
        y: int,
        text: str,
        fg: tuple[int, int, int] | None = None,
        bg: tuple[int, int, int] | None = None,
        bold: bool = False,
    ) -> None:
        """Write text horizontally starting at (x, y).

        Args:
            x: Starting column.
            y: Row.
            text: Text to write.
            fg: Foreground color (RGB).
            bg: Background color (RGB).
            bold: Bold attribute.
        """
        for i, char in enumerate(text):
            self.set(x + i, y, Cell(char=char, fg=fg, bg=bg, bold=bold))

    def clone(self) -> Buffer:
        """Create an independent copy of this buffer."""
        new_buf = Buffer(self.width, self.height)
        new_buf._cells = [
            Cell(
                char=c.char,
                fg=c.fg,
                bg=c.bg,
                bold=c.bold,
                dim=c.dim,
                italic=c.italic,
                underline=c.underline,
            )
            for c in self._cells
        ]
        return new_buf
