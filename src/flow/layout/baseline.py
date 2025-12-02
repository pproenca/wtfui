# src/flow/layout/baseline.py
"""Baseline alignment calculation (matches Yoga's algorithm/Baseline.cpp)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode


def calculate_baseline(node: LayoutNode) -> float:
    """Calculate the baseline of a node.

    If the node has a baseline_func, use it.
    Otherwise, recursively find the baseline from the first appropriate child.
    If no baseline can be found, return the node's height.

    Args:
        node: The layout node to calculate baseline for.

    Returns:
        The baseline offset from the top of the node.
    """
    from flow.layout.style import AlignItems, Position

    # If node has explicit baseline function, use it
    if node.has_baseline_func() and node.baseline_func is not None:
        result = node.baseline_func(node.layout.width, node.layout.height)
        return result if result is not None else node.layout.height

    # Find first child that qualifies for baseline
    baseline_child: LayoutNode | None = None

    for child in node.children:
        # Skip absolute positioned children
        if child.style.position == Position.ABSOLUTE:
            continue

        # Prefer children with align-self: baseline
        effective_align = child.style.align_self or node.style.align_items
        if effective_align == AlignItems.BASELINE:
            baseline_child = child
            break

        # Otherwise use first non-absolute child
        if baseline_child is None:
            baseline_child = child

    if baseline_child is None:
        # No suitable child found, use own height
        return node.layout.height

    # Recursively get child's baseline and add its y position
    child_baseline = calculate_baseline(baseline_child)
    return child_baseline + baseline_child.layout.y


def is_baseline_layout(node: LayoutNode) -> bool:
    """Check if this node uses baseline alignment.

    Baseline alignment only applies to row direction (horizontal).
    Returns True if align-items is baseline or any child has align-self baseline.

    Args:
        node: The layout node to check.

    Returns:
        True if baseline alignment should be used.
    """
    from flow.layout.style import AlignItems, Position

    # Baseline only applies to row direction
    if node.style.flex_direction.is_column():
        return False

    # Check if container uses baseline alignment
    if node.style.align_items == AlignItems.BASELINE:
        return True

    # Check if any child uses align-self: baseline
    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            continue
        if child.style.align_self == AlignItems.BASELINE:
            return True

    return False
