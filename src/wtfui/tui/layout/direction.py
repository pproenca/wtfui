from wtfui.tui.layout.style import Direction, FlexDirection


def resolve_flex_direction(
    flex_direction: FlexDirection,
    direction: Direction,
) -> FlexDirection:
    if direction == Direction.RTL:
        if flex_direction == FlexDirection.ROW:
            return FlexDirection.ROW_REVERSE
        if flex_direction == FlexDirection.ROW_REVERSE:
            return FlexDirection.ROW

    return flex_direction
