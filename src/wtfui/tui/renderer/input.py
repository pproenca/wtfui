from dataclasses import dataclass

CTRL_C = "\x03"
CTRL_D = "\x04"
CTRL_O = "\x0f"
CTRL_Z = "\x1a"
ESCAPE = "\x1b"
ENTER = "\r"
BACKSPACE = "\x7f"


@dataclass
class KeyEvent:
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


@dataclass
class MouseEvent:
    x: int
    y: int
    button: int
    pressed: bool

    @property
    def is_move(self) -> bool:
        return self.button >= 32 and self.button <= 35

    @property
    def is_scroll_up(self) -> bool:
        return self.button == 64

    @property
    def is_scroll_down(self) -> bool:
        return self.button == 65


@dataclass
class ResizeEvent:
    width: int
    height: int


ESCAPE_SEQUENCES: dict[str, str] = {
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1b[H": "home",
    "\x1b[F": "end",
    "\x1b[3~": "delete",
    "\x1b[5~": "page_up",
    "\x1b[6~": "page_down",
    "\x1bOP": "f1",
    "\x1bOQ": "f2",
    "\x1bOR": "f3",
    "\x1bOS": "f4",
}


def parse_input_sequence(seq: str) -> KeyEvent | MouseEvent:
    if not seq:
        return KeyEvent(key="")

    if seq.startswith("\x1b[<"):
        try:
            body = seq[3:]
            pressed = body.endswith("M")
            params = body[:-1]

            parts = params.split(";")
            if len(parts) == 3:
                button = int(parts[0])
                x = int(parts[1]) - 1
                y = int(parts[2]) - 1
                return MouseEvent(x=x, y=y, button=button, pressed=pressed)
        except (ValueError, IndexError):
            pass

    return parse_key_sequence(seq)


def parse_key_sequence(seq: str) -> KeyEvent:
    if not seq:
        return KeyEvent(key="")

    if seq in ESCAPE_SEQUENCES:
        return KeyEvent(key=ESCAPE_SEQUENCES[seq])

    if seq == ESCAPE:
        return KeyEvent(key="escape")

    if seq in ("\r", "\n"):
        return KeyEvent(key="enter")

    if seq == BACKSPACE or seq == "\x08":
        return KeyEvent(key="backspace")

    if seq == "\t":
        return KeyEvent(key="tab")

    if len(seq) == 1:
        code = ord(seq)
        if 1 <= code <= 26:
            char = chr(code + 96)
            return KeyEvent(key=char, ctrl=True)

    if len(seq) == 1:
        return KeyEvent(key=seq)

    return KeyEvent(key=seq)


async def read_key_async() -> str:
    import asyncio
    import sys

    char = await asyncio.to_thread(sys.stdin.read, 1)

    if char == ESCAPE:
        try:
            import select

            if select.select([sys.stdin], [], [], 0.05)[0]:
                extra = ""
                while select.select([sys.stdin], [], [], 0.01)[0]:
                    extra += sys.stdin.read(1)
                return char + extra
        except OSError:
            pass

    return char
