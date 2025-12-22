ESC = "\x1b"
CSI = f"{ESC}["


def cursor_move(x: int, y: int) -> str:
    return f"{CSI}{y + 1};{x + 1}H"


def cursor_hide() -> str:
    return f"{CSI}?25l"


def cursor_show() -> str:
    return f"{CSI}?25h"


def clear_screen() -> str:
    return f"{CSI}2J"


def clear_line() -> str:
    return f"{CSI}2K"


def clear_from_cursor_down() -> str:
    return f"{CSI}J"


def cursor_home() -> str:
    return f"{CSI}H"


def reset_scroll_region() -> str:
    return f"{CSI}r"


def set_fg_rgb(r: int, g: int, b: int) -> str:
    return f"{CSI}38;2;{r};{g};{b}m"


def set_bg_rgb(r: int, g: int, b: int) -> str:
    return f"{CSI}48;2;{r};{g};{b}m"


def reset_style() -> str:
    return f"{CSI}0m"


def set_bold() -> str:
    return f"{CSI}1m"


def set_dim() -> str:
    return f"{CSI}2m"


def set_italic() -> str:
    return f"{CSI}3m"


def set_underline() -> str:
    return f"{CSI}4m"


def enter_alt_screen() -> str:
    return f"{CSI}?1049h"


def exit_alt_screen() -> str:
    return f"{CSI}?1049l"


def enable_mouse_tracking() -> str:
    return f"{CSI}?1000h{CSI}?1003h{CSI}?1006h"


def disable_mouse_tracking() -> str:
    return f"{CSI}?1006l{CSI}?1003l{CSI}?1000l"
