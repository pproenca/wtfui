# src/flow/layout/intrinsic.py
"""Intrinsic sizing calculations for min-content, max-content, and fit-content."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode


def calculate_min_content_width(node: LayoutNode) -> float:
    """Calculate the min-content width for a node.

    Min-content width is the smallest width that doesn't cause overflow,
    typically determined by the widest word or fixed-width element.

    For flex containers, this is the sum of children's min-content widths
    (for row) or the maximum of children's min-content widths (for column).

    Args:
        node: The layout node to calculate min-content for.

    Returns:
        The min-content width in pixels.
    """
    style = node.style

    # If width is explicitly set (not auto/intrinsic), use that
    if style.width.is_defined() and not style.width.is_intrinsic():
        return style.width.value or 0

    # Base case: leaf node with no children
    if not node.children:
        # Could have intrinsic content (text, images) but we don't model that
        return 0

    # Calculate based on children
    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        # Row: sum of children's min-content widths + gaps
        total = sum(calculate_min_content_width(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total
    else:
        # Column: max of children's min-content widths
        return max((calculate_min_content_width(c) for c in node.children), default=0)


def calculate_max_content_width(node: LayoutNode) -> float:
    """Calculate the max-content width for a node.

    Max-content width is the ideal width without any wrapping,
    typically the full natural width of the content.

    For flex containers, this is the sum of children's max-content widths
    (for row) or the maximum of children's max-content widths (for column).

    Args:
        node: The layout node to calculate max-content for.

    Returns:
        The max-content width in pixels.
    """
    style = node.style

    # If width is explicitly set (not auto/intrinsic), use that
    if style.width.is_defined() and not style.width.is_intrinsic():
        return style.width.value or 0

    # Base case: leaf node with no children
    if not node.children:
        return 0

    # Calculate based on children
    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        # Row: sum of children's max-content widths + gaps
        total = sum(calculate_max_content_width(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total
    else:
        # Column: max of children's max-content widths
        return max((calculate_max_content_width(c) for c in node.children), default=0)


def calculate_min_content_height(node: LayoutNode) -> float:
    """Calculate the min-content height for a node.

    Args:
        node: The layout node to calculate min-content height for.

    Returns:
        The min-content height in pixels.
    """
    style = node.style

    # If height is explicitly set (not auto/intrinsic), use that
    if style.height.is_defined() and not style.height.is_intrinsic():
        return style.height.value or 0

    # Base case: leaf node
    if not node.children:
        return 0

    # Calculate based on children
    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        # Row: max of children's min-content heights
        return max((calculate_min_content_height(c) for c in node.children), default=0)
    else:
        # Column: sum of children's min-content heights + gaps
        total = sum(calculate_min_content_height(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total


def calculate_max_content_height(node: LayoutNode) -> float:
    """Calculate the max-content height for a node.

    Args:
        node: The layout node to calculate max-content height for.

    Returns:
        The max-content height in pixels.
    """
    style = node.style

    # If height is explicitly set (not auto/intrinsic), use that
    if style.height.is_defined() and not style.height.is_intrinsic():
        return style.height.value or 0

    # Base case: leaf node
    if not node.children:
        return 0

    # Calculate based on children
    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        # Row: max of children's max-content heights
        return max((calculate_max_content_height(c) for c in node.children), default=0)
    else:
        # Column: sum of children's max-content heights + gaps
        total = sum(calculate_max_content_height(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total


def calculate_fit_content_width(
    node: LayoutNode, available: float, max_clamp: float | None = None
) -> float:
    """Calculate the fit-content width for a node.

    Fit-content is clamped between min-content and max-content,
    further constrained by available space and optional max_clamp.

    fit-content = min(max-content, max(min-content, available))

    Args:
        node: The layout node to calculate fit-content for.
        available: Available width from parent.
        max_clamp: Optional maximum clamp value.

    Returns:
        The fit-content width in pixels.
    """
    min_w = calculate_min_content_width(node)
    max_w = calculate_max_content_width(node)

    # fit-content formula
    result = min(max_w, max(min_w, available))

    # Apply optional clamp
    if max_clamp is not None:
        result = min(result, max_clamp)

    return result


def calculate_fit_content_height(
    node: LayoutNode, available: float, max_clamp: float | None = None
) -> float:
    """Calculate the fit-content height for a node.

    Args:
        node: The layout node to calculate fit-content for.
        available: Available height from parent.
        max_clamp: Optional maximum clamp value.

    Returns:
        The fit-content height in pixels.
    """
    min_h = calculate_min_content_height(node)
    max_h = calculate_max_content_height(node)

    # fit-content formula
    result = min(max_h, max(min_h, available))

    # Apply optional clamp
    if max_clamp is not None:
        result = min(result, max_clamp)

    return result
