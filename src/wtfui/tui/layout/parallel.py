from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from wtfui.tui.layout.algorithm import (
    align_cross_axis_with_baseline,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from wtfui.tui.layout.flexline import collect_flex_lines
from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import AlignContent, Position

if TYPE_CHECKING:
    from wtfui.tui.layout.types import Size

DEFAULT_MAX_WORKERS = 4


MIN_CHILDREN_FOR_PARALLEL = 3


def find_layout_boundaries(root: LayoutNode) -> list[LayoutNode]:
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
    from wtfui.tui.layout.compute import compute_layout

    if not node.children or len(node.children) < MIN_CHILDREN_FOR_PARALLEL:
        compute_layout(node, available)
        return

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
    from wtfui.tui.layout.compute import _clamp_size, _resolve_dimension_with_intrinsic

    style = node.style

    width = _resolve_dimension_with_intrinsic(style.width, available.width, node, is_width=True)
    height = _resolve_dimension_with_intrinsic(style.height, available.height, node, is_width=False)

    if style.aspect_ratio is not None:
        from wtfui.tui.layout.compute import _apply_aspect_ratio

        width, height = _apply_aspect_ratio(
            width, height, style.aspect_ratio, available.width, available.height
        )
    else:
        if width is None:
            width = available.width
        if height is None:
            height = available.height

    width = _clamp_size(width, style.min_width, style.max_width, available.width)
    height = _clamp_size(height, style.min_height, style.max_height, available.height)

    node.layout = LayoutResult(x=0, y=0, width=width, height=height)

    if node.children:
        _layout_children_parallel(node, executor)

    node.clear_dirty()


def _layout_children_parallel(node: LayoutNode, executor: ThreadPoolExecutor) -> None:
    style = node.style
    direction = style.flex_direction
    is_row = direction.is_row()

    padding = style.padding.resolve(node.layout.width, node.layout.height)
    inner_width = node.layout.width - padding.horizontal
    inner_height = node.layout.height - padding.vertical

    container_main = inner_width if is_row else inner_height
    container_cross = inner_height if is_row else inner_width

    gap = style.get_gap(direction)

    flex_items: list[LayoutNode] = []
    absolute_items: list[LayoutNode] = []
    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            absolute_items.append(child)
        else:
            flex_items.append(child)

    lines = collect_flex_lines(
        items=flex_items,
        container_main=container_main,
        wrap=style.flex_wrap,
        gap=gap,
        direction=direction,
    )

    cross_gap = style.row_gap if is_row and style.row_gap is not None else style.gap
    if not is_row and style.column_gap is not None:
        cross_gap = style.column_gap

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

        cross_results = align_cross_axis_with_baseline(
            items=line.items,
            item_sizes=cross_sizes,
            container_cross=line.cross_size,
            align=style.align_items,
            is_row=is_row,
        )

        line_data.append((main_sizes, main_positions, cross_results))

    effective_align_content = style.align_content
    if style.flex_wrap.is_no_wrap():
        effective_align_content = AlignContent.FLEX_START

    from wtfui.tui.layout.compute import _distribute_align_content

    line_offsets = _distribute_align_content(
        line_sizes=[line.cross_size for line in lines],
        container_cross=container_cross,
        align_content=effective_align_content,
        gap=cross_gap,
    )

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

            if item.children:
                children_to_layout.append(item)

    from wtfui.tui.layout.compute import _layout_children

    if len(children_to_layout) >= MIN_CHILDREN_FOR_PARALLEL:
        futures = [executor.submit(_layout_children, child) for child in children_to_layout]

        for future in futures:
            future.result()
    else:
        for child in children_to_layout:
            _layout_children(child)

    from wtfui.tui.layout.compute import _layout_absolute_child

    for abs_child in absolute_items:
        _layout_absolute_child(abs_child, node.layout.width, node.layout.height)
