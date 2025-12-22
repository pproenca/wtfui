from typing import TYPE_CHECKING

from wtfui.tui.layout.algorithm import (
    align_cross_axis_with_baseline,
    apply_auto_margins,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from wtfui.tui.layout.direction import resolve_flex_direction
from wtfui.tui.layout.flexline import collect_flex_lines
from wtfui.tui.layout.intrinsic import (
    calculate_fit_content_height,
    calculate_fit_content_width,
    calculate_max_content_height,
    calculate_max_content_width,
    calculate_min_content_height,
    calculate_min_content_width,
)
from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import AlignContent, Position
from wtfui.tui.layout.types import Dimension, DimensionUnit

if TYPE_CHECKING:
    from wtfui.tui.layout.node import MeasureMode
    from wtfui.tui.layout.types import Size


def compute_layout(node: LayoutNode, available: Size) -> None:
    from wtfui.tui.layout.node import MeasureMode

    style = node.style

    if node.measure_func is not None and not node.children:
        measured_width, measured_height = _measure_node_with_cache(
            node=node,
            available_width=available.width,
            available_height=available.height,
            width_mode=MeasureMode.EXACTLY if style.width.is_defined() else MeasureMode.AT_MOST,
            height_mode=MeasureMode.EXACTLY if style.height.is_defined() else MeasureMode.AT_MOST,
        )
        node.layout = LayoutResult(x=0, y=0, width=measured_width, height=measured_height)
        node.clear_dirty()
        return

    width: float | None = _resolve_dimension_with_intrinsic(
        style.width, available.width, node, is_width=True
    )
    height: float | None = _resolve_dimension_with_intrinsic(
        style.height, available.height, node, is_width=False
    )

    if style.aspect_ratio is not None:
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
        _layout_children(node)

    node.clear_dirty()


def _measure_node_with_cache(
    node: LayoutNode,
    available_width: float,
    available_height: float,
    width_mode: MeasureMode,
    height_mode: MeasureMode,
) -> tuple[float, float]:
    from wtfui.tui.layout.cache import can_use_cached_measurement
    from wtfui.tui.layout.node import CachedMeasurement

    if (
        node.cached_measurement is not None
        and not node.is_dirty()
        and can_use_cached_measurement(
            cache=node.cached_measurement,
            available_width=available_width,
            available_height=available_height,
            width_mode=width_mode,
            height_mode=height_mode,
        )
    ):
        return (
            node.cached_measurement.computed_width,
            node.cached_measurement.computed_height,
        )

    assert node.measure_func is not None
    result = node.measure_func(available_width, available_height)

    node.cached_measurement = CachedMeasurement(
        available_width=available_width,
        available_height=available_height,
        width_mode=width_mode,
        height_mode=height_mode,
        computed_width=result.width,
        computed_height=result.height,
    )

    return result.width, result.height


def _clamp_size(
    value: float,
    min_dim: Dimension,
    max_dim: Dimension,
    parent: float,
) -> float:
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
    if dim._unit == DimensionUnit.MIN_CONTENT:
        if is_width:
            return calculate_min_content_width(node)
        return calculate_min_content_height(node)

    if dim._unit == DimensionUnit.MAX_CONTENT:
        if is_width:
            return calculate_max_content_width(node)
        return calculate_max_content_height(node)

    if dim._unit == DimensionUnit.FIT_CONTENT:
        max_clamp = dim.value
        if is_width:
            return calculate_fit_content_width(node, available, max_clamp)
        return calculate_fit_content_height(node, available, max_clamp)

    return dim.resolve(available)


def _apply_aspect_ratio(
    width: float | None,
    height: float | None,
    aspect_ratio: float,
    available_width: float,
    available_height: float,
) -> tuple[float, float]:
    if width is not None and height is not None:
        return width, height

    if width is not None:
        return width, width / aspect_ratio

    if height is not None:
        return height * aspect_ratio, height

    return available_width, available_width / aspect_ratio


def _layout_children(node: LayoutNode) -> None:
    style = node.style

    direction = resolve_flex_direction(style.flex_direction, style.direction)
    is_row = direction.is_row()

    padding = style.padding.resolve(node.layout.width, node.layout.height)
    border = style.border
    inner_width = node.layout.width - padding.horizontal - border.horizontal
    inner_height = node.layout.height - padding.vertical - border.vertical

    container_main = inner_width if is_row else inner_height
    container_cross = inner_height if is_row else inner_width

    gap = style.get_gap(direction)

    flex_items: list[LayoutNode] = []
    absolute_items: list[LayoutNode] = []
    hidden_items: list[LayoutNode] = []

    for child in node.children:
        from wtfui.tui.layout.style import Display

        if child.style.display == Display.NONE:
            hidden_items.append(child)
        elif child.style.position == Position.ABSOLUTE:
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

        main_positions = apply_auto_margins(
            items=line.items,
            positions=main_positions,
            sizes=main_sizes,
            container_size=container_main,
            is_row=is_row,
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

    total_lines_cross = sum(line.cross_size for line in lines)
    total_lines_cross += cross_gap * max(0, len(lines) - 1)

    effective_align_content = style.align_content
    if style.flex_wrap.is_no_wrap():
        effective_align_content = AlignContent.FLEX_START

    line_offsets = _distribute_align_content(
        line_sizes=[line.cross_size for line in lines],
        container_cross=container_cross,
        align_content=effective_align_content,
        gap=cross_gap,
    )

    for line_idx, line in enumerate(lines):
        main_sizes, main_positions, cross_results = line_data[line_idx]
        cross_offset = (
            border.top + padding.top if is_row else border.left + padding.left
        ) + line_offsets[line_idx]

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

            if direction.is_reverse():
                if is_row:
                    main_pos = container_main - main_pos - main_size
                else:
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

            if item.children:
                _layout_children(item)

    for abs_child in absolute_items:
        _layout_absolute_child(abs_child, node.layout.width, node.layout.height)

    for hidden_child in hidden_items:
        hidden_child.layout = LayoutResult(x=0, y=0, width=0, height=0)

        if hidden_child.children:
            _layout_children(hidden_child)


def _distribute_align_content(
    line_sizes: list[float],
    container_cross: float,
    align_content: AlignContent,
    gap: float,
) -> list[float]:
    from wtfui.tui.layout.style import AlignContent

    if not line_sizes:
        return []

    num_lines = len(line_sizes)
    total_lines_size = sum(line_sizes)
    total_gap = gap * max(0, num_lines - 1)
    remaining = container_cross - total_lines_size - total_gap

    offsets: list[float] = []

    if align_content == AlignContent.FLEX_START:
        offset = 0.0
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.FLEX_END:
        offset = remaining
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.CENTER:
        offset = remaining / 2
        for size in line_sizes:
            offsets.append(offset)
            offset += size + gap

    elif align_content == AlignContent.SPACE_BETWEEN:
        if num_lines == 1:
            offsets.append(0.0)
        else:
            space_between = (remaining + total_gap) / (num_lines - 1)
            offset = 0.0
            for size in line_sizes:
                offsets.append(offset)
                offset += size + space_between

    elif align_content == AlignContent.SPACE_AROUND:
        space_per_line = (remaining + total_gap) / num_lines
        offset = space_per_line / 2
        for size in line_sizes:
            offsets.append(offset)
            offset += size + space_per_line

    elif align_content == AlignContent.SPACE_EVENLY:
        num_gaps = num_lines + 1
        space_per_gap = (remaining + total_gap) / num_gaps
        offset = space_per_gap
        for size in line_sizes:
            offsets.append(offset)
            offset += size + space_per_gap

    elif align_content == AlignContent.STRETCH:
        if num_lines == 1:
            offsets.append(0.0)
        else:
            stretched_size = container_cross / num_lines
            offset = 0.0
            for _ in line_sizes:
                offsets.append(offset)
                offset += stretched_size

    else:
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
    style = child.style

    top = style.top.resolve(container_height)
    right = style.right.resolve(container_width)
    bottom = style.bottom.resolve(container_height)
    left = style.left.resolve(container_width)

    width = style.width.resolve(container_width)
    height = style.height.resolve(container_height)

    if left is not None:
        x = left
    elif right is not None and width is not None:
        x = container_width - right - width
    elif right is not None:
        x = 0
    else:
        x = 0

    if top is not None:
        y = top
    elif bottom is not None and height is not None:
        y = container_height - bottom - height
    elif bottom is not None:
        y = 0
    else:
        y = 0

    if width is None:
        width = container_width - left - right if left is not None and right is not None else 0

    if height is None:
        height = (
            container_height - top - bottom
            if top is not None and bottom is not None
            else container_height
        )

    width = _clamp_size(width, style.min_width, style.max_width, container_width)
    height = _clamp_size(height, style.min_height, style.max_height, container_height)

    child.layout = LayoutResult(x=x, y=y, width=width, height=height)

    if child.children:
        _layout_children(child)
