from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.layout.node import LayoutNode
    from wtfui.tui.layout.style import AlignItems, FlexDirection, JustifyContent


class SizingMode(Enum):
    CONTENT_BOX = "content-box"
    BORDER_BOX = "border-box"

    def is_content_box(self) -> bool:
        return self == SizingMode.CONTENT_BOX

    def is_border_box(self) -> bool:
        return self == SizingMode.BORDER_BOX


@dataclass(frozen=True)
class AvailableSpace:
    _value: float | None
    _mode: str

    @classmethod
    def definite(cls, value: float) -> AvailableSpace:
        return cls(value, "definite")

    @classmethod
    def min_content(cls) -> AvailableSpace:
        return cls(None, "min-content")

    @classmethod
    def max_content(cls) -> AvailableSpace:
        return cls(None, "max-content")

    def is_definite(self) -> bool:
        return self._mode == "definite"

    def is_min_content(self) -> bool:
        return self._mode == "min-content"

    def is_max_content(self) -> bool:
        return self._mode == "max-content"

    @property
    def value(self) -> float | None:
        return self._value

    def resolve(self) -> float:
        if self._value is not None:
            return self._value
        return 0.0 if self.is_min_content() else float("inf")


def resolve_flexible_lengths(
    items: list[LayoutNode],
    container_main_size: float,
    direction: FlexDirection,
    gap: float,
) -> list[float]:
    if not items:
        return []

    total_gap = gap * (len(items) - 1) if len(items) > 1 else 0
    available_space = container_main_size - total_gap

    bases: list[float] = []
    for item in items:
        basis = item.style.flex_basis
        if basis.is_defined():
            bases.append(basis.resolve(container_main_size) or 0)
        else:
            dim = item.style.width if direction.is_row() else item.style.height
            resolved = dim.resolve(container_main_size)
            if resolved is not None:
                bases.append(resolved)
            else:
                from wtfui.tui.layout.intrinsic import (
                    calculate_min_content_height,
                    calculate_min_content_width,
                )

                if direction.is_row():
                    bases.append(calculate_min_content_width(item))
                else:
                    bases.append(calculate_min_content_height(item))

    total_basis = sum(bases)
    free_space = available_space - total_basis

    if free_space >= 0:
        total_grow = sum(item.style.flex_grow for item in items)
        if total_grow == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_grow / total_grow))
            for base, item in zip(bases, items, strict=False)
        ]
    else:
        total_shrink = sum(
            item.style.flex_shrink * base for base, item in zip(bases, items, strict=False)
        )
        if total_shrink == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_shrink * base / total_shrink))
            for base, item in zip(bases, items, strict=False)
        ]


def distribute_justify_content(
    item_sizes: list[float],
    container_size: float,
    justify: JustifyContent,
    gap: float,
) -> list[float]:
    from wtfui.tui.layout.style import JustifyContent

    if not item_sizes:
        return []

    n = len(item_sizes)
    total_item_size = sum(item_sizes)
    total_gap = gap * (n - 1) if n > 1 else 0
    free_space = container_size - total_item_size - total_gap

    positions: list[float] = []

    if justify == JustifyContent.FLEX_START:
        pos = 0.0
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.FLEX_END:
        pos = free_space
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.CENTER:
        pos = free_space / 2
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.SPACE_BETWEEN:
        if n == 1:
            positions.append(0.0)
        else:
            spacing = free_space / (n - 1)
            pos = 0.0
            for size in item_sizes:
                positions.append(pos)
                pos += size + spacing

    elif justify == JustifyContent.SPACE_AROUND:
        spacing = free_space / n
        pos = spacing / 2
        for size in item_sizes:
            positions.append(pos)
            pos += size + spacing

    elif justify == JustifyContent.SPACE_EVENLY:
        spacing = free_space / (n + 1)
        pos = spacing
        for size in item_sizes:
            positions.append(pos)
            pos += size + spacing

    return positions


def align_cross_axis(
    item_sizes: list[float],
    container_cross: float,
    align: AlignItems,
) -> list[tuple[float, float]]:
    from wtfui.tui.layout.style import AlignItems

    if not item_sizes:
        return []

    results: list[tuple[float, float]] = []

    for size in item_sizes:
        if align == AlignItems.STRETCH:
            results.append((0, container_cross))

        elif align == AlignItems.FLEX_START:
            results.append((0, size))

        elif align == AlignItems.FLEX_END:
            results.append((container_cross - size, size))

        elif align == AlignItems.CENTER:
            pos = (container_cross - size) / 2
            results.append((pos, size))

        elif align == AlignItems.BASELINE:
            results.append((0, size))

        else:
            results.append((0, size))

    return results


def _prepare_layout_for_baseline(node: LayoutNode, cross_size: float) -> None:
    if node.layout.height == 0:
        h = node.style.height.resolve(cross_size)
        if h is not None:
            node.layout.height = h
        else:
            node.layout.height = cross_size

    if node.layout.width == 0:
        w = node.style.width.resolve(cross_size)
        if w is not None:
            node.layout.width = w

    for child in node.children:
        _prepare_layout_for_baseline(child, node.layout.height)


def align_cross_axis_with_baseline(
    items: list[LayoutNode],
    item_sizes: list[float],
    container_cross: float,
    align: AlignItems,
    is_row: bool,
) -> list[tuple[float, float]]:
    from wtfui.tui.layout.style import AlignItems

    if not items:
        return []

    results: list[tuple[float, float]] = []

    needs_baseline = is_row and (
        align == AlignItems.BASELINE
        or any(item.style.align_self == AlignItems.BASELINE for item in items)
    )

    if needs_baseline:
        from wtfui.tui.layout.baseline import calculate_baseline

        baselines: list[float] = []
        max_baseline = 0.0

        for item, size in zip(items, item_sizes, strict=True):
            effective_align = item.style.align_self or align
            if effective_align == AlignItems.BASELINE:
                _prepare_layout_for_baseline(item, size)

                baseline = calculate_baseline(item)
                baselines.append(baseline)
                max_baseline = max(max_baseline, baseline)
            else:
                baselines.append(-1)

        for i, (item, size) in enumerate(zip(items, item_sizes, strict=True)):
            effective_align = item.style.align_self or align

            if effective_align == AlignItems.BASELINE and baselines[i] >= 0:
                pos = max_baseline - baselines[i]
                results.append((pos, size))

            elif effective_align == AlignItems.STRETCH:
                results.append((0, container_cross))

            elif effective_align == AlignItems.FLEX_START:
                results.append((0, size))

            elif effective_align == AlignItems.FLEX_END:
                results.append((container_cross - size, size))

            elif effective_align == AlignItems.CENTER:
                pos = (container_cross - size) / 2
                results.append((pos, size))

            else:
                results.append((0, size))
    else:
        for item, size in zip(items, item_sizes, strict=True):
            effective_align = item.style.align_self or align

            if effective_align == AlignItems.STRETCH:
                results.append((0, container_cross))

            elif effective_align == AlignItems.FLEX_START:
                results.append((0, size))

            elif effective_align == AlignItems.FLEX_END:
                results.append((container_cross - size, size))

            elif effective_align == AlignItems.CENTER:
                pos = (container_cross - size) / 2
                results.append((pos, size))

            else:
                results.append((0, size))

    return results


def apply_auto_margins(
    items: list[LayoutNode],
    positions: list[float],
    sizes: list[float],
    container_size: float,
    is_row: bool,
) -> list[float]:
    if not items:
        return positions

    adjusted = list(positions)

    if len(items) == 1:
        margin = items[0].style.margin
        size = sizes[0]

        all_auto = (
            margin.left_is_auto()
            and margin.right_is_auto()
            and margin.top_is_auto()
            and margin.bottom_is_auto()
        )

        if all_auto:
            return adjusted

        has_free_space = container_size > size

        if is_row and has_free_space:
            left_auto = margin.left_is_auto()
            right_auto = margin.right_is_auto()

            if left_auto and right_auto:
                remaining = container_size - size
                adjusted[0] = remaining / 2
            elif left_auto and not right_auto:
                adjusted[0] = container_size - size

        elif not is_row and has_free_space:
            top_auto = margin.top_is_auto()
            bottom_auto = margin.bottom_is_auto()

            if top_auto and bottom_auto:
                remaining = container_size - size
                adjusted[0] = remaining / 2
            elif top_auto and not bottom_auto:
                adjusted[0] = container_size - size

    return adjusted
