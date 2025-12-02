# src/flow/layout/flexline.py
"""Flex line collection for wrapping support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexDirection, FlexWrap


@dataclass
class FlexLine:
    """A single line of flex items."""

    items: list[LayoutNode] = field(default_factory=list)
    cross_size: float = 0.0  # Height of this line (in row direction)
    main_size: float = 0.0  # Used width of this line


def collect_flex_lines(
    items: list[LayoutNode],
    container_main: float,
    wrap: FlexWrap,
    gap: float,
    direction: FlexDirection | None = None,
) -> list[FlexLine]:
    """Collect flex items into lines based on wrap mode.

    Implements CSS Flexbox spec section 9.3:
    https://www.w3.org/TR/css-flexbox-1/#algo-line-break

    Args:
        items: List of LayoutNodes to distribute into lines.
        container_main: Available space in the main axis.
        wrap: FlexWrap mode (no-wrap, wrap, wrap-reverse).
        gap: Gap between items.
        direction: FlexDirection for determining main axis dimension.

    Returns:
        List of FlexLine objects containing item groups.
    """
    from flow.layout.style import FlexWrap

    if not items:
        return []

    if wrap == FlexWrap.NO_WRAP:
        # All items in single line
        return [FlexLine(items=list(items))]

    # Default to row if direction not specified
    is_row = direction.is_row() if direction else True

    lines: list[FlexLine] = []
    current_line: list[LayoutNode] = []
    current_main = 0.0

    for item in items:
        # Get item's hypothetical main size
        item_main = _get_hypothetical_main_size(item, container_main, is_row)

        # Check if item fits on current line
        gap_to_add = gap if current_line else 0
        if current_line and current_main + gap_to_add + item_main > container_main:
            # Start new line
            lines.append(FlexLine(items=current_line, main_size=current_main))
            current_line = [item]
            current_main = item_main
        else:
            current_line.append(item)
            current_main += gap_to_add + item_main

    # Add last line
    if current_line:
        lines.append(FlexLine(items=current_line, main_size=current_main))

    return lines


def _get_hypothetical_main_size(
    item: LayoutNode, container_main: float, is_row: bool = True
) -> float:
    """Get the hypothetical main size of a flex item.

    Args:
        item: The LayoutNode to measure.
        container_main: Container size in the main axis.
        is_row: True if row direction (use width), False for column (use height).

    Returns:
        The hypothetical main size in pixels.
    """
    style = item.style

    # Check flex-basis first
    if style.flex_basis.is_defined():
        return style.flex_basis.resolve(container_main) or 0

    # Fall back to width/height based on direction
    dim = style.width if is_row else style.height
    if dim.is_defined():
        return dim.resolve(container_main) or 0

    # Auto - needs content sizing (simplified to 0 for now)
    return 0
