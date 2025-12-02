# src/flow/layout/compute.py
"""Main layout computation algorithm for the Flow Layout Engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flow.layout.algorithm import (
    align_cross_axis,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from flow.layout.flexline import collect_flex_lines
from flow.layout.node import LayoutResult
from flow.layout.style import Position

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.types import Dimension, Size


def compute_layout(node: LayoutNode, available: Size) -> None:
    """Compute layout for a node tree.

    This is the main entry point for the Flexbox algorithm.
    Implements CSS Flexbox spec:
    https://www.w3.org/TR/css-flexbox-1/

    Args:
        node: The root LayoutNode to compute layout for.
        available: Available Size (width, height) for the root node.
    """
    # Resolve node's own size
    style = node.style

    width = style.width.resolve(available.width)
    height = style.height.resolve(available.height)

    # Apply aspect ratio if set
    if style.aspect_ratio is not None:
        width, height = _apply_aspect_ratio(
            width, height, style.aspect_ratio, available.width, available.height
        )
    else:
        # Default to available size if not specified
        if width is None:
            width = available.width
        if height is None:
            height = available.height

    # Apply min/max constraints
    width = _clamp_size(width, style.min_width, style.max_width, available.width)
    height = _clamp_size(height, style.min_height, style.max_height, available.height)

    # Set node's layout
    node.layout = LayoutResult(x=0, y=0, width=width, height=height)

    # Layout children if any
    if node.children:
        _layout_children(node)

    node.clear_dirty()


def _clamp_size(
    value: float,
    min_dim: Dimension,
    max_dim: Dimension,
    parent: float,
) -> float:
    """Clamp value between min and max dimensions."""
    min_val = min_dim.resolve(parent) if min_dim.is_defined() else 0
    max_val = max_dim.resolve(parent) if max_dim.is_defined() else float("inf")

    return max(min_val or 0, min(value, max_val or float("inf")))


def _apply_aspect_ratio(
    width: float | None,
    height: float | None,
    aspect_ratio: float,
    available_width: float,
    available_height: float,
) -> tuple[float, float]:
    """Apply aspect ratio to calculate missing dimension.

    Aspect ratio is defined as width / height.
    - If width is known, height = width / aspect_ratio
    - If height is known, width = height * aspect_ratio
    - If neither is known, use available space and aspect ratio

    Args:
        width: Resolved width (or None if auto).
        height: Resolved height (or None if auto).
        aspect_ratio: The width:height ratio (e.g., 2.0 means 2:1).
        available_width: Available width for fallback.
        available_height: Available height for fallback.

    Returns:
        Tuple of (width, height) with aspect ratio applied.
    """
    if width is not None and height is not None:
        # Both specified - aspect ratio doesn't apply
        return width, height

    if width is not None:
        # Calculate height from width
        return width, width / aspect_ratio

    if height is not None:
        # Calculate width from height
        return height * aspect_ratio, height

    # Neither specified - use available space
    # Try to fit within available space maintaining aspect ratio
    return available_width, available_width / aspect_ratio


def _layout_children(node: LayoutNode) -> None:
    """Layout children using Flexbox algorithm."""

    style = node.style
    direction = style.flex_direction
    is_row = direction.is_row()

    # Get container inner size (subtract padding)
    padding = style.padding.resolve(node.layout.width, node.layout.height)
    inner_width = node.layout.width - padding.horizontal
    inner_height = node.layout.height - padding.vertical

    container_main = inner_width if is_row else inner_height
    container_cross = inner_height if is_row else inner_width

    gap = style.get_gap(direction)

    # Separate flex items from absolute positioned children
    flex_items: list[LayoutNode] = []
    absolute_items: list[LayoutNode] = []
    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            absolute_items.append(child)
        else:
            flex_items.append(child)

    # Collect flex items into flex lines (absolute items are excluded)
    lines = collect_flex_lines(
        items=flex_items,
        container_main=container_main,
        wrap=style.flex_wrap,
        gap=gap,
        direction=direction,
    )

    # Resolve flexible lengths for each line
    cross_offset = padding.top if is_row else padding.left

    for line in lines:
        # Get main axis sizes
        main_sizes = resolve_flexible_lengths(
            items=line.items,
            container_main_size=container_main,
            direction=direction,
            gap=gap,
        )

        # Get main axis positions (justify-content)
        main_positions = distribute_justify_content(
            item_sizes=main_sizes,
            container_size=container_main,
            justify=style.justify_content,
            gap=gap,
        )

        # Calculate cross sizes for alignment (considering aspect ratio)
        cross_sizes = []
        for idx, item in enumerate(line.items):
            if is_row:
                h = item.style.height.resolve(container_cross)
                if h is None and item.style.aspect_ratio is not None:
                    # Calculate height from width using aspect ratio
                    h = main_sizes[idx] / item.style.aspect_ratio
                cross_sizes.append(h if h else container_cross)
            else:
                w = item.style.width.resolve(container_cross)
                if w is None and item.style.aspect_ratio is not None:
                    # Calculate width from height using aspect ratio
                    w = main_sizes[idx] * item.style.aspect_ratio
                cross_sizes.append(w if w else container_cross)

        # Determine line cross size
        line.cross_size = max(cross_sizes) if cross_sizes else container_cross

        # Get cross axis positions (align-items)
        cross_results = align_cross_axis(
            item_sizes=cross_sizes,
            container_cross=line.cross_size,
            align=style.align_items,
        )

        # Apply layouts to children
        for i, item in enumerate(line.items):
            main_pos = main_positions[i]
            main_size = main_sizes[i]
            cross_pos, cross_size = cross_results[i]

            if is_row:
                x = padding.left + main_pos
                y = cross_offset + cross_pos
                w = main_size
                h = cross_size
            else:
                x = cross_offset + cross_pos
                y = padding.top + main_pos
                w = cross_size
                h = main_size

            item.layout = LayoutResult(x=x, y=y, width=w, height=h)

            # Recursively layout grandchildren
            if item.children:
                _layout_children(item)

        # Move cross offset for next line (for wrap)
        # Row direction uses row_gap between lines, column uses column_gap
        if is_row:
            cross_gap = style.row_gap if style.row_gap is not None else style.gap
        else:
            cross_gap = style.column_gap if style.column_gap is not None else style.gap
        cross_offset += line.cross_size + cross_gap

    # Layout absolute positioned children
    for abs_child in absolute_items:
        _layout_absolute_child(abs_child, node.layout.width, node.layout.height)


def _layout_absolute_child(
    child: LayoutNode,
    container_width: float,
    container_height: float,
) -> None:
    """Layout an absolutely positioned child.

    Absolute children are positioned relative to their containing block
    using inset properties (top, right, bottom, left).

    Args:
        child: The absolute positioned child node.
        container_width: Width of the containing block.
        container_height: Height of the containing block.
    """
    style = child.style

    # Resolve insets (percentages are relative to container size)
    top = style.top.resolve(container_height)
    right = style.right.resolve(container_width)
    bottom = style.bottom.resolve(container_height)
    left = style.left.resolve(container_width)

    # Resolve explicit dimensions
    width = style.width.resolve(container_width)
    height = style.height.resolve(container_height)

    # Calculate x position
    if left is not None:
        x = left
    elif right is not None and width is not None:
        x = container_width - right - width
    elif right is not None:
        # Width derived from left (0) and right
        x = 0
    else:
        x = 0  # Default to left edge

    # Calculate y position
    if top is not None:
        y = top
    elif bottom is not None and height is not None:
        y = container_height - bottom - height
    elif bottom is not None:
        # Height derived from top (0) and bottom
        y = 0
    else:
        y = 0  # Default to top edge

    # Calculate dimensions if not explicit
    if width is None:
        # Stretch between left and right, or default to 0
        width = container_width - left - right if left is not None and right is not None else 0

    if height is None:
        # Stretch between top and bottom, or default to container height
        height = (
            container_height - top - bottom
            if top is not None and bottom is not None
            else container_height
        )

    # Apply min/max constraints
    width = _clamp_size(width, style.min_width, style.max_width, container_width)
    height = _clamp_size(height, style.min_height, style.max_height, container_height)

    child.layout = LayoutResult(x=x, y=y, width=width, height=height)

    # Recursively layout children of absolute child
    if child.children:
        _layout_children(child)
