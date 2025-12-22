from dataclasses import dataclass


@dataclass(slots=True)
class Cell:
    char: str = " "
    fg: tuple[int, int, int] | None = None
    bg: tuple[int, int, int] | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False

    def reset(self) -> None:
        self.char = " "
        self.fg = None
        self.bg = None
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
