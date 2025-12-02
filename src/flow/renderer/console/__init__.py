"""Console Renderer - Terminal-based rendering with double buffering."""

from flow.renderer.console import ansi
from flow.renderer.console.buffer import Buffer
from flow.renderer.console.cell import Cell
from flow.renderer.console.diff import DiffResult, diff_buffers
from flow.renderer.console.renderer import ConsoleRenderer
from flow.renderer.console.theme import PALETTE, apply_cls_to_cell

__all__ = [
    "PALETTE",
    "Buffer",
    "Cell",
    "ConsoleRenderer",
    "DiffResult",
    "ansi",
    "apply_cls_to_cell",
    "diff_buffers",
]
