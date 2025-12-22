from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.layout.node import LayoutNode
    from wtfui.tui.layout.style import FlexDirection, FlexWrap


@dataclass
class FlexLine:
    items: list[LayoutNode] = field(default_factory=list)
    cross_size: float = 0.0
    main_size: float = 0.0


def collect_flex_lines(
    items: list[LayoutNode],
    container_main: float,
    wrap: FlexWrap,
    gap: float,
    direction: FlexDirection | None = None,
) -> list[FlexLine]:
    from wtfui.tui.layout.style import FlexWrap

    if not items:
        return []

    if wrap == FlexWrap.NO_WRAP:
        return [FlexLine(items=list(items))]

    is_row = direction.is_row() if direction else True

    lines: list[FlexLine] = []
    current_line: list[LayoutNode] = []
    current_main = 0.0

    for item in items:
        item_main = _get_hypothetical_main_size(item, container_main, is_row)

        gap_to_add = gap if current_line else 0
        if current_line and current_main + gap_to_add + item_main > container_main:
            lines.append(FlexLine(items=current_line, main_size=current_main))
            current_line = [item]
            current_main = item_main
        else:
            current_line.append(item)
            current_main += gap_to_add + item_main

    if current_line:
        lines.append(FlexLine(items=current_line, main_size=current_main))

    return lines


def _get_hypothetical_main_size(
    item: LayoutNode, container_main: float, is_row: bool = True
) -> float:
    style = item.style

    if style.flex_basis.is_defined():
        return style.flex_basis.resolve(container_main) or 0

    dim = style.width if is_row else style.height
    if dim.is_defined():
        return dim.resolve(container_main) or 0

    return 0
