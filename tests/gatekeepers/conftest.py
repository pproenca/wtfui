"""Shared fixtures for Gatekeeper tests."""

import gc

import pytest

from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle
from flow.layout.types import Dimension


@pytest.fixture
def clean_gc():
    """Force garbage collection before and after test."""
    gc.collect()
    yield
    gc.collect()


def generate_deep_layout_tree(depth: int, width: int = 2) -> LayoutNode:
    """Generate a layout tree for stress testing.

    Creates a tree with `depth` levels, each node having `width` children.
    Total nodes = (width^(depth+1) - 1) / (width - 1) for width > 1.

    Args:
        depth: Number of levels in the tree.
        width: Number of children per node.

    Returns:
        Root LayoutNode of the generated tree.
    """

    def build_node(current_depth: int) -> LayoutNode:
        style = FlexStyle(
            width=Dimension.points(100),
            height=Dimension.points(50),
        )
        node = LayoutNode(style=style)

        if current_depth < depth:
            for _ in range(width):
                child = build_node(current_depth + 1)
                node.add_child(child)

        return node

    return build_node(0)


def count_nodes(node: LayoutNode) -> int:
    """Count total nodes in a layout tree."""
    count = 1
    for child in node.children:
        count += count_nodes(child)
    return count
