# src/flow/renderer/console/theme.py
"""Console theme - Tailwind-style color palette for terminal rendering.

Maps Tailwind CSS color classes to RGB values for TrueColor terminals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.renderer.console.cell import Cell

# Standard Tailwind CSS palette mapped to RGB
# https://tailwindcss.com/docs/customizing-colors
PALETTE: dict[str, tuple[int, int, int]] = {
    # Slate
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
    # Red
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
    # Green
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
    # Blue
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
    # Yellow
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
    # White/Black
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def apply_cls_to_cell(cell: Cell, cls: str) -> None:
    """Apply Tailwind-style classes to a Cell.

    Parses class string like "bg-red-500 text-white bold"
    and modifies cell attributes accordingly.

    Args:
        cell: The cell to modify (in place).
        cls: Space-separated class names.
    """
    parts = cls.split()
    for part in parts:
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
