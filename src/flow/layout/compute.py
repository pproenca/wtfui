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
    if width is None:
        width = available.width

    height = style.height.resolve(available.height)
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

    # Collect items into flex lines
    lines = collect_flex_lines(
        items=node.children,
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

        # Calculate cross sizes for alignment
        cross_sizes = []
        for item in line.items:
            if is_row:
                h = item.style.height.resolve(container_cross)
                cross_sizes.append(h if h else container_cross)
            else:
                w = item.style.width.resolve(container_cross)
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
