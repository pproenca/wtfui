# src/flow/layout/direction.py
"""Direction resolution for RTL/LTR support (matches Yoga's FlexDirection.h)."""

from __future__ import annotations

from flow.layout.style import Direction, FlexDirection


def resolve_flex_direction(
    flex_direction: FlexDirection,
    direction: Direction,
) -> FlexDirection:
    """Resolve flex direction based on layout direction (LTR/RTL).

    In RTL mode, row and row-reverse are swapped.
    Column directions are unaffected.

    Args:
        flex_direction: The flex-direction style property.
        direction: The layout direction (LTR or RTL).

    Returns:
        The resolved flex direction.

    Examples:
        >>> resolve_flex_direction(FlexDirection.ROW, Direction.RTL)
        FlexDirection.ROW_REVERSE

        >>> resolve_flex_direction(FlexDirection.COLUMN, Direction.RTL)
        FlexDirection.COLUMN
    """
    if direction == Direction.RTL:
        if flex_direction == FlexDirection.ROW:
            return FlexDirection.ROW_REVERSE
        if flex_direction == FlexDirection.ROW_REVERSE:
            return FlexDirection.ROW

    return flex_direction
