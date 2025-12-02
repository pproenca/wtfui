# src/flow/layout/compute.py
"""Main layout computation algorithm for the Flow Layout Engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flow.layout.algorithm import (
    align_cross_axis_with_baseline,
    apply_auto_margins,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from flow.layout.direction import resolve_flex_direction
from flow.layout.flexline import collect_flex_lines
from flow.layout.intrinsic import (
    calculate_fit_content_height,
    calculate_fit_content_width,
    calculate_max_content_height,
    calculate_max_content_width,
    calculate_min_content_height,
    calculate_min_content_width,
)
from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import AlignContent, Position
from flow.layout.types import Dimension, DimensionUnit

if TYPE_CHECKING:
    from flow.layout.types import Size


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

    # Handle intrinsic dimensions
    width = _resolve_dimension_with_intrinsic(style.width, available.width, node, is_width=True)
    height = _resolve_dimension_with_intrinsic(style.height, available.height, node, is_width=False)

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


def _resolve_dimension_with_intrinsic(
    dim: Dimension,
    available: float,
    node: LayoutNode,
    *,
    is_width: bool,
) -> float | None:
    """Resolve a dimension that may be an intrinsic size.

    Args:
        dim: The dimension to resolve.
        available: Available space in this direction.
        node: The layout node (for intrinsic size calculation).
        is_width: True for width, False for height.

    Returns:
        Resolved value in pixels, or None if auto.
    """
    if dim._unit == DimensionUnit.MIN_CONTENT:
        if is_width:
            return calculate_min_content_width(node)
        return calculate_min_content_height(node)

    if dim._unit == DimensionUnit.MAX_CONTENT:
        if is_width:
            return calculate_max_content_width(node)
        return calculate_max_content_height(node)

    if dim._unit == DimensionUnit.FIT_CONTENT:
        max_clamp = dim.value  # Optional clamp stored in value
        if is_width:
            return calculate_fit_content_width(node, available, max_clamp)
        return calculate_fit_content_height(node, available, max_clamp)

    # Regular dimension (auto, points, percent)
    return dim.resolve(available)


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

    # Resolve flex direction based on layout direction (RTL/LTR)
    direction = resolve_flex_direction(style.flex_direction, style.direction)
    is_row = direction.is_row()

    # Get container inner size (subtract padding and border)
    padding = style.padding.resolve(node.layout.width, node.layout.height)
    border = style.border
    inner_width = node.layout.width - padding.horizontal - border.horizontal
    inner_height = node.layout.height - padding.vertical - border.vertical

    container_main = inner_width if is_row else inner_height
    container_cross = inner_height if is_row else inner_width

    gap = style.get_gap(direction)

    # Separate flex items from absolute positioned and display:none children
    flex_items: list[LayoutNode] = []
    absolute_items: list[LayoutNode] = []
    hidden_items: list[LayoutNode] = []

    for child in node.children:
        from flow.layout.style import Display

        if child.style.display == Display.NONE:
            # Elements with display:none are excluded from layout
            hidden_items.append(child)
        elif child.style.position == Position.ABSOLUTE:
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

    # Cross gap between lines
    cross_gap = style.row_gap if is_row and style.row_gap is not None else style.gap
    if not is_row and style.column_gap is not None:
        cross_gap = style.column_gap

    # First pass: calculate line cross sizes and main axis layout data
    line_data: list[tuple[list[float], list[float], list[tuple[float, float]]]] = []

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

        # Apply auto margins (overrides justify-content for items with auto margins)
        main_positions = apply_auto_margins(
            items=line.items,
            positions=main_positions,
            sizes=main_sizes,
            container_size=container_main,
            is_row=is_row,
        )

        # Calculate cross sizes for alignment (considering aspect ratio)
        cross_sizes = []
        for idx, item in enumerate(line.items):
            if is_row:
                h = item.style.height.resolve(container_cross)
                if h is None and item.style.aspect_ratio is not None:
                    h = main_sizes[idx] / item.style.aspect_ratio
                cross_sizes.append(h if h else container_cross)
            else:
                w = item.style.width.resolve(container_cross)
                if w is None and item.style.aspect_ratio is not None:
                    w = main_sizes[idx] * item.style.aspect_ratio
                cross_sizes.append(w if w else container_cross)

        # Determine line cross size
        line.cross_size = max(cross_sizes) if cross_sizes else container_cross

        # Get cross axis positions (align-items within line)
        # Use baseline-aware alignment to handle align-items: baseline
        cross_results = align_cross_axis_with_baseline(
            items=line.items,
            item_sizes=cross_sizes,
            container_cross=line.cross_size,
            align=style.align_items,
            is_row=is_row,
        )

        line_data.append((main_sizes, main_positions, cross_results))

    # Calculate total lines cross size
    total_lines_cross = sum(line.cross_size for line in lines)
    total_lines_cross += cross_gap * max(0, len(lines) - 1)

    # Apply align-content to determine line offsets
    # Note: align-content only applies to multi-line containers (wrap enabled)
    effective_align_content = style.align_content
    if style.flex_wrap.is_no_wrap():
        # Single-line container: align-content has no effect, use flex-start
        effective_align_content = AlignContent.FLEX_START

    line_offsets = _distribute_align_content(
        line_sizes=[line.cross_size for line in lines],
        container_cross=container_cross,
        align_content=effective_align_content,
        gap=cross_gap,
    )

    # Second pass: position items using calculated offsets
    for line_idx, line in enumerate(lines):
        main_sizes, main_positions, cross_results = line_data[line_idx]
        cross_offset = (
            border.top + padding.top if is_row else border.left + padding.left
        ) + line_offsets[line_idx]

        # For stretch, update line cross size
        if effective_align_content == AlignContent.STRETCH and len(lines) > 1:
            line.cross_size = container_cross / len(lines)

        for i, item in enumerate(line.items):
            main_pos = main_positions[i]
            main_size = main_sizes[i]
            cross_pos, cross_size = cross_results[i]

            # For align-content: stretch, expand items without explicit cross size
            if effective_align_content == AlignContent.STRETCH and len(lines) > 1:
                if (is_row and item.style.height.is_auto()) or (
                    not is_row and item.style.width.is_auto()
                ):
                    cross_size = line.cross_size
                cross_pos = 0

            # Apply reverse direction by flipping positions
            if direction.is_reverse():
                if is_row:
                    # In row-reverse, flip horizontally within container
                    main_pos = container_main - main_pos - main_size
                else:
                    # In column-reverse, flip vertically within container
                    main_pos = container_main - main_pos - main_size

            if is_row:
                x = border.left + padding.left + main_pos
                y = cross_offset + cross_pos
                w = main_size
                h = cross_size
            else:
                x = cross_offset + cross_pos
                y = border.top + padding.top + main_pos
                w = cross_size
                h = main_size

            item.layout = LayoutResult(x=x, y=y, width=w, height=h)

            # Recursively layout grandchildren
            if item.children:
                _layout_children(item)

    # Layout absolute positioned children
    for abs_child in absolute_items:
        _layout_absolute_child(abs_child, node.layout.width, node.layout.height)

    # Set hidden children to zero size
    for hidden_child in hidden_items:
        hidden_child.layout = LayoutResult(x=0, y=0, width=0, height=0)
        # Recursively set descendants to zero size as well
        if hidden_child.children:
            _layout_children(hidden_child)


def _distribute_align_content(
    line_sizes: list[float],
    container_cross: float,
    align_content: AlignContent,
    gap: float,
) -> list[float]:
    """Calculate line offsets based on align-content.

    Args:
        line_sizes: Cross size of each flex line.
        container_cross: Available cross-axis space.
        align_content: The align-content value.
        gap: Gap between lines.

    Returns:
        List of offsets for each line from the cross-axis start.
    """
    from flow.layout.style import AlignContent

    if not line_sizes:
        return []

    num_lines = len(line_sizes)
    total_lines_size = sum(line_sizes)
    total_gap = gap * max(0, num_lines - 1)
    remaining = container_cross - total_lines_size - total_gap

    offsets: list[float] = []

    if align_content == AlignContent.FLEX_START:
        # Lines packed at start
        offset = 0.0
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.FLEX_END:
        # Lines packed at end
        offset = remaining
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.CENTER:
        # Lines centered
        offset = remaining / 2
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.SPACE_BETWEEN:
        # First line at start, last at end, space distributed between
        if num_lines == 1:
            offsets.append(0.0)
        else:
            space_between = (remaining + total_gap) / (num_lines - 1)
            offset = 0.0
            for size in line_sizes:
                offsets.append(offset)
                offset += size + space_between

    elif align_content == AlignContent.SPACE_AROUND:
        # Space distributed around each line (half-space at edges)
        space_per_line = (remaining + total_gap) / num_lines
        offset = space_per_line / 2
        for size in line_sizes:
            offsets.append(offset)
            offset += size + space_per_line

    elif align_content == AlignContent.SPACE_EVENLY:
        # Space distributed evenly (including edges)
        # n lines = n+1 gaps (before, between each, after)
        num_gaps = num_lines + 1
        space_per_gap = (remaining + total_gap) / num_gaps
        offset = space_per_gap
        for size in line_sizes:
            offsets.append(offset)
            offset += size + space_per_gap

    elif align_content == AlignContent.STRETCH:
        # Lines stretched to fill container (handled separately in layout)
        # For offsets, distribute evenly
        if num_lines == 1:
            offsets.append(0.0)
        else:
            stretched_size = container_cross / num_lines
            offset = 0.0
            for _ in line_sizes:
                offsets.append(offset)
                offset += stretched_size

    else:
        # Default to flex-start
        offset = 0.0
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    return offsets


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
