from wtfui.tui.renderer.cell import Cell


class Buffer:
    __slots__ = ("_cells", "height", "width")

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

        self._cells = [Cell() for _ in range(width * height)]

    def _index(self, x: int, y: int) -> int | None:
        if 0 <= x < self.width and 0 <= y < self.height:
            return y * self.width + x
        return None

    def get(self, x: int, y: int) -> Cell:
        idx = self._index(x, y)
        if idx is not None:
            return self._cells[idx]
        return Cell()

    def set(self, x: int, y: int, cell: Cell) -> None:
        idx = self._index(x, y)
        if idx is not None:
            self._cells[idx] = cell

    def clear(self) -> None:
        for cell in self._cells:
            cell.reset()

    def write_text(
        self,
        x: int,
        y: int,
        text: str,
        fg: tuple[int, int, int] | None = None,
        bg: tuple[int, int, int] | None = None,
        bold: bool = False,
    ) -> None:
        for i, char in enumerate(text):
            self.set(x + i, y, Cell(char=char, fg=fg, bg=bg, bold=bold))

    def clone(self) -> Buffer:
        new_buf = Buffer.__new__(Buffer)
        new_buf.width = self.width
        new_buf.height = self.height
        new_buf._cells = list(self._cells)
        return new_buf
