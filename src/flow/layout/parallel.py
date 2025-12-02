# src/flow/layout/parallel.py
"""Parallel layout computation for No-GIL Python 3.14+.

This module provides parallel layout computation by processing independent
subtrees concurrently using ThreadPoolExecutor. With Python 3.14's No-GIL
mode, this enables true parallel execution for CPU-bound layout calculations.

The parallelization strategy:
1. Root node layout is computed first (determines container constraints)
2. Direct children are laid out sequentially to determine their positions
3. Grandchildren subtrees are computed in parallel (they don't affect each other)

This approach avoids the overhead of recursive parallelism while still
benefiting from parallel execution of independent subtrees.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from flow.layout.algorithm import (
    align_cross_axis,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from flow.layout.flexline import collect_flex_lines
from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import AlignContent, Position

if TYPE_CHECKING:
    from flow.layout.types import Size


# Default number of workers for parallel layout
DEFAULT_MAX_WORKERS = 4

# Minimum children count to trigger parallel execution
# Below this threshold, overhead of parallelism exceeds benefits
MIN_CHILDREN_FOR_PARALLEL = 3


def find_layout_boundaries(root: LayoutNode) -> list[LayoutNode]:
    """Find all Layout Boundary nodes in a tree.

    A Layout Boundary is a node with explicit width AND height.
    These nodes can be computed in parallel since their layout
    doesn't depend on content size.

    Args:
        root: The root node to search from.

    Returns:
        List of Layout Boundary nodes (excluding root).
    """
    boundaries: list[LayoutNode] = []

    def _find_recursive(node: LayoutNode, include_self: bool = False) -> None:
        if include_self and node.is_layout_boundary():
            boundaries.append(node)
        for child in node.children:
            _find_recursive(child, include_self=True)

    _find_recursive(root, include_self=False)
    return boundaries


def compute_layout_parallel(
    node: LayoutNode,
    available: Size,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> None:
    """Compute layout for a node tree using parallel execution.

    This is the parallel version of compute_layout that can leverage
    Python 3.14's No-GIL mode for true parallel execution.

    The parallelization occurs at depth 1: after computing the root and
    its direct children's layouts, grandchildren subtrees are processed
    in parallel since siblings don't affect each other.

    Args:
        node: The root LayoutNode to compute layout for.
        available: Available Size (width, height) for the root node.
        executor: Optional ThreadPoolExecutor for parallel execution.
                 If not provided, a default executor is created.
    """
    from flow.layout.compute import compute_layout

    # For simple trees, just use sequential layout
    if not node.children or len(node.children) < MIN_CHILDREN_FOR_PARALLEL:
        compute_layout(node, available)
        return

    # Create or use provided executor
    if executor is None:
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as pool:
            _compute_parallel_with_executor(node, available, pool)
    else:
        _compute_parallel_with_executor(node, available, executor)


def _compute_parallel_with_executor(
    node: LayoutNode,
    available: Size,
    executor: ThreadPoolExecutor,
) -> None:
    """Internal parallel layout computation with provided executor.

    Args:
        node: The root LayoutNode.
        available: Available Size for the root node.
        executor: The ThreadPoolExecutor to use.
    """
    from flow.layout.compute import _clamp_size, _resolve_dimension_with_intrinsic

    style = node.style

    # Resolve node's own size
    width = _resolve_dimension_with_intrinsic(style.width, available.width, node, is_width=True)
    height = _resolve_dimension_with_intrinsic(style.height, available.height, node, is_width=False)

    # Apply aspect ratio if set
    if style.aspect_ratio is not None:
        from flow.layout.compute import _apply_aspect_ratio

        width, height = _apply_aspect_ratio(
            width, height, style.aspect_ratio, available.width, available.height
        )
    else:
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
        _layout_children_parallel(node, executor)

    node.clear_dirty()


def _layout_children_parallel(node: LayoutNode, executor: ThreadPoolExecutor) -> None:
    """Layout children using parallel execution for independent subtrees.

    The parallelization occurs at the grandchild level - after computing
    each child's layout, we can compute grandchildren in parallel since
    siblings don't affect each other's layout.

    Args:
        node: The parent node with children to layout.
        executor: The ThreadPoolExecutor for parallel execution.
    """
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

    # Collect flex items into flex lines
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

    # First pass: calculate line cross sizes and layout data
    line_data: list[tuple[list[float], list[float], list[tuple[float, float]]]] = []

    for line in lines:
        main_sizes = resolve_flexible_lengths(
            items=line.items,
            container_main_size=container_main,
            direction=direction,
            gap=gap,
        )

        main_positions = distribute_justify_content(
            item_sizes=main_sizes,
            container_size=container_main,
            justify=style.justify_content,
            gap=gap,
        )

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

        line.cross_size = max(cross_sizes) if cross_sizes else container_cross

        cross_results = align_cross_axis(
            item_sizes=cross_sizes,
            container_cross=line.cross_size,
            align=style.align_items,
        )

        line_data.append((main_sizes, main_positions, cross_results))

    # Apply align-content
    effective_align_content = style.align_content
    if style.flex_wrap.is_no_wrap():
        effective_align_content = AlignContent.FLEX_START

    from flow.layout.compute import _distribute_align_content

    line_offsets = _distribute_align_content(
        line_sizes=[line.cross_size for line in lines],
        container_cross=container_cross,
        align_content=effective_align_content,
        gap=cross_gap,
    )

    # Second pass: position items and collect subtrees to process
    children_to_layout: list[LayoutNode] = []

    for line_idx, line in enumerate(lines):
        main_sizes, main_positions, cross_results = line_data[line_idx]
        cross_offset = (padding.top if is_row else padding.left) + line_offsets[line_idx]

        if effective_align_content == AlignContent.STRETCH and len(lines) > 1:
            line.cross_size = container_cross / len(lines)

        for i, item in enumerate(line.items):
            main_pos = main_positions[i]
            main_size = main_sizes[i]
            cross_pos, cross_size = cross_results[i]

            if effective_align_content == AlignContent.STRETCH and len(lines) > 1:
                if (is_row and item.style.height.is_auto()) or (
                    not is_row and item.style.width.is_auto()
                ):
                    cross_size = line.cross_size
                cross_pos = 0

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

            # Collect children with grandchildren for parallel processing
            if item.children:
                children_to_layout.append(item)

    # Process child subtrees in parallel if enough children
    # Use sequential layout for subtrees to avoid recursive parallelism overhead
    from flow.layout.compute import _layout_children

    if len(children_to_layout) >= MIN_CHILDREN_FOR_PARALLEL:
        futures = [executor.submit(_layout_children, child) for child in children_to_layout]
        # Wait for all to complete
        for future in futures:
            future.result()
    else:
        # Sequential fallback for small number of children
        for child in children_to_layout:
            _layout_children(child)

    # Layout absolute positioned children (sequential, typically few)
    from flow.layout.compute import _layout_absolute_child

    for abs_child in absolute_items:
        _layout_absolute_child(abs_child, node.layout.width, node.layout.height)
