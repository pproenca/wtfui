# src/flow/layout/style.py
"""Flexbox style enums and FlexStyle dataclass."""

from __future__ import annotations

from enum import Enum


class FlexDirection(Enum):
    """Main axis direction for flex layout."""

    ROW = "row"
    COLUMN = "column"
    ROW_REVERSE = "row-reverse"
    COLUMN_REVERSE = "column-reverse"

    def is_row(self) -> bool:
        """Check if direction is horizontal (row or row-reverse)."""
        return self in (FlexDirection.ROW, FlexDirection.ROW_REVERSE)

    def is_column(self) -> bool:
        """Check if direction is vertical (column or column-reverse)."""
        return self in (FlexDirection.COLUMN, FlexDirection.COLUMN_REVERSE)

    def is_reverse(self) -> bool:
        """Check if direction is reversed."""
        return self in (FlexDirection.ROW_REVERSE, FlexDirection.COLUMN_REVERSE)


class FlexWrap(Enum):
    """Wrapping behavior for flex items."""

    NO_WRAP = "nowrap"
    WRAP = "wrap"
    WRAP_REVERSE = "wrap-reverse"

    def is_no_wrap(self) -> bool:
        """Check if wrapping is disabled."""
        return self == FlexWrap.NO_WRAP

    def is_wrap(self) -> bool:
        """Check if wrapping is enabled."""
        return self in (FlexWrap.WRAP, FlexWrap.WRAP_REVERSE)

    def is_reverse(self) -> bool:
        """Check if wrap direction is reversed."""
        return self == FlexWrap.WRAP_REVERSE


class JustifyContent(Enum):
    """Main axis alignment for flex items."""

    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class AlignItems(Enum):
    """Cross axis alignment for flex items."""

    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"


class AlignContent(Enum):
    """Cross axis alignment for flex lines (multi-line)."""

    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"


class Position(Enum):
    """Positioning mode for elements."""

    RELATIVE = "relative"
    ABSOLUTE = "absolute"
