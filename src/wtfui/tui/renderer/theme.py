from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.core.style import Style
    from wtfui.tui.renderer.cell import Cell

from wtfui.tui.renderer.manifest import css_color_to_rgb, get_manifest

PALETTE: dict[str, tuple[int, int, int]] = {
    "slate-50": (248, 250, 252),
    "slate-100": (241, 245, 249),
    "slate-200": (226, 232, 240),
    "slate-300": (203, 213, 225),
    "slate-400": (148, 163, 184),
    "slate-500": (100, 116, 139),
    "slate-600": (71, 85, 105),
    "slate-700": (51, 65, 85),
    "slate-800": (30, 41, 59),
    "slate-900": (15, 23, 42),
    "slate-950": (2, 6, 23),
    "red-50": (254, 242, 242),
    "red-100": (254, 226, 226),
    "red-200": (254, 202, 202),
    "red-300": (252, 165, 165),
    "red-400": (248, 113, 113),
    "red-500": (239, 68, 68),
    "red-600": (220, 38, 38),
    "red-700": (185, 28, 28),
    "red-800": (153, 27, 27),
    "red-900": (127, 29, 29),
    "green-50": (240, 253, 244),
    "green-100": (220, 252, 231),
    "green-200": (187, 247, 208),
    "green-300": (134, 239, 172),
    "green-400": (74, 222, 128),
    "green-500": (34, 197, 94),
    "green-600": (22, 163, 74),
    "green-700": (21, 128, 61),
    "green-800": (22, 101, 52),
    "green-900": (20, 83, 45),
    "blue-50": (239, 246, 255),
    "blue-100": (219, 234, 254),
    "blue-200": (191, 219, 254),
    "blue-300": (147, 197, 253),
    "blue-400": (96, 165, 250),
    "blue-500": (59, 130, 246),
    "blue-600": (37, 99, 235),
    "blue-700": (29, 78, 216),
    "blue-800": (30, 64, 175),
    "blue-900": (30, 58, 138),
    "yellow-50": (254, 252, 232),
    "yellow-100": (254, 249, 195),
    "yellow-200": (254, 240, 138),
    "yellow-300": (253, 224, 71),
    "yellow-400": (250, 204, 21),
    "yellow-500": (234, 179, 8),
    "yellow-600": (202, 138, 4),
    "yellow-700": (161, 98, 7),
    "yellow-800": (133, 77, 14),
    "yellow-900": (113, 63, 18),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def apply_cls_to_cell(cell: Cell, cls: str) -> None:
    parts = cls.split()
    manifest = get_manifest()

    for part in parts:
        if part.startswith("fl-") and manifest:
            props = manifest.resolve(part)
            if props:
                _apply_css_props_to_cell(cell, props)
                continue

        if part.startswith("bg-"):
            color_name = part[3:]
            if color_name in PALETTE:
                cell.bg = PALETTE[color_name]
        elif part.startswith("text-"):
            color_name = part[5:]
            if color_name in PALETTE:
                cell.fg = PALETTE[color_name]
        elif part == "bold":
            cell.bold = True
        elif part == "dim":
            cell.dim = True
        elif part == "italic":
            cell.italic = True
        elif part == "underline":
            cell.underline = True


def _parse_color(color: str | None) -> tuple[int, int, int] | None:
    if not color:
        return None

    if color in PALETTE:
        return PALETTE[color]

    hex_str = color.lstrip("#")
    if len(hex_str) == 6:
        try:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b)
        except ValueError:
            pass

    return None


def apply_style_to_cell(cell: Cell, style: Style) -> None:
    fg = _parse_color(style.color)
    if fg:
        cell.fg = fg

    bg = _parse_color(style.bg)
    if bg:
        cell.bg = bg

    if style.font_weight == "bold":
        cell.bold = True

    if style.text_decoration == "underline":
        cell.underline = True
    elif style.text_decoration == "line-through":
        cell.dim = True

    if style.opacity is not None and style.opacity < 1.0:
        cell.dim = True


def _apply_css_props_to_cell(cell: Cell, props: dict[str, str]) -> None:
    for prop, value in props.items():
        if prop == "background-color":
            rgb = css_color_to_rgb(value)
            if rgb:
                cell.bg = rgb
        elif prop == "color":
            rgb = css_color_to_rgb(value)
            if rgb:
                cell.fg = rgb
        elif prop == "font-weight" and value in ("bold", "700", "800", "900"):
            cell.bold = True
