"""Layout test utilities.

Separated from conftest.py to avoid pytest double-import issues.
"""

from wtfui.tui.layout.node import LayoutNode
from wtfui.tui.layout.style import FlexStyle
from wtfui.tui.layout.types import Dimension


def generate_wide_layout_tree(width: int) -> LayoutNode:
    """Generate a flat layout tree with many siblings."""
    root = LayoutNode(
        style=FlexStyle(
            width=Dimension.points(1920),
            height=Dimension.points(1080),
        )
    )
    for _ in range(width):
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )
        root.add_child(child)
    return root


def generate_deep_layout_tree(depth: int, width: int = 1) -> LayoutNode:
    """Generate a layout tree with specified depth and branching factor."""
    root = LayoutNode(
        style=FlexStyle(
            width=Dimension.points(1920),
            height=Dimension.points(1080),
        )
    )

    def build_level(parent: LayoutNode, remaining_depth: int) -> None:
        if remaining_depth <= 0:
            return
        for _ in range(width):
            child = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(100),
                    height=Dimension.points(50),
                )
            )
            parent.add_child(child)
            build_level(child, remaining_depth - 1)

    build_level(root, depth)
    return root
