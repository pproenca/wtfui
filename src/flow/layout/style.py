# src/flow/layout/style.py
"""Flexbox style enums and FlexStyle dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

from flow.layout.types import Border, Dimension, Spacing


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
    SPACE_EVENLY = "space-evenly"  # Matches Yoga's Align::SpaceEvenly


class Position(Enum):
    """Positioning mode for elements."""

    STATIC = "static"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"

    def is_static(self) -> bool:
        """Check if position is static (normal flow, no offsets)."""
        return self == Position.STATIC

    def is_positioned(self) -> bool:
        """Check if position is relative or absolute (allows offsets)."""
        return self in (Position.RELATIVE, Position.ABSOLUTE)


class Display(Enum):
    """Display mode for elements (matches Yoga's Display enum)."""

    FLEX = "flex"
    NONE = "none"
    CONTENTS = "contents"

    def is_visible(self) -> bool:
        """Check if element should be rendered."""
        return self != Display.NONE

    def is_contents(self) -> bool:
        """Check if element should act as if replaced by children."""
        return self == Display.CONTENTS


class Direction(Enum):
    """Text/layout direction (LTR or RTL)."""

    INHERIT = "inherit"
    LTR = "ltr"
    RTL = "rtl"

    def is_ltr(self) -> bool:
        """Check if left-to-right."""
        return self == Direction.LTR

    def is_rtl(self) -> bool:
        """Check if right-to-left."""
        return self == Direction.RTL


class Overflow(Enum):
    """Overflow behavior for elements."""

    VISIBLE = "visible"
    HIDDEN = "hidden"
    SCROLL = "scroll"

    def allows_overflow(self) -> bool:
        """Check if content can overflow the bounds."""
        return self == Overflow.VISIBLE

    def is_scrollable(self) -> bool:
        """Check if scrollbars should be shown."""
        return self == Overflow.SCROLL


class BoxSizing(Enum):
    """Box sizing model (border-box or content-box)."""

    BORDER_BOX = "border-box"
    CONTENT_BOX = "content-box"

    def includes_padding(self) -> bool:
        """Check if padding is included in width/height."""
        return self == BoxSizing.BORDER_BOX


@dataclass(frozen=True, slots=True)
class FlexStyle:
    """Complete flexbox style definition for a layout node.

    This dataclass contains all CSS Flexbox properties needed for layout
    computation. It's immutable (frozen) for thread safety with No-GIL.
    """

    # Display & Position
    display: Display = Display.FLEX
    position: Position = Position.RELATIVE
    direction: Direction = Direction.INHERIT
    overflow: Overflow = Overflow.VISIBLE
    box_sizing: BoxSizing = BoxSizing.BORDER_BOX

    # Flex Container Properties
    flex_direction: FlexDirection = FlexDirection.ROW
    flex_wrap: FlexWrap = FlexWrap.NO_WRAP
    justify_content: JustifyContent = JustifyContent.FLEX_START
    align_items: AlignItems = AlignItems.STRETCH
    align_content: AlignContent = AlignContent.STRETCH

    # Flex Item Properties
    flex_grow: float = 0.0
    flex_shrink: float = 1.0
    flex_basis: Dimension = field(default_factory=Dimension.auto)
    align_self: AlignItems | None = None

    # Sizing
    width: Dimension = field(default_factory=Dimension.auto)
    height: Dimension = field(default_factory=Dimension.auto)
    min_width: Dimension = field(default_factory=Dimension.auto)
    min_height: Dimension = field(default_factory=Dimension.auto)
    max_width: Dimension = field(default_factory=Dimension.auto)
    max_height: Dimension = field(default_factory=Dimension.auto)
    aspect_ratio: float | None = None

    # Spacing
    margin: Spacing = field(default_factory=Spacing)
    padding: Spacing = field(default_factory=Spacing)
    border: Border = field(default_factory=Border.zero)
    gap: float = 0.0
    row_gap: float | None = None
    column_gap: float | None = None

    # Position offsets (for position: absolute)
    top: Dimension = field(default_factory=Dimension.auto)
    right: Dimension = field(default_factory=Dimension.auto)
    bottom: Dimension = field(default_factory=Dimension.auto)
    left: Dimension = field(default_factory=Dimension.auto)

    def with_updates(self, **kwargs: object) -> FlexStyle:
        """Create a new FlexStyle with the specified fields updated."""
        return replace(self, **kwargs)  # type: ignore[arg-type]

    def get_gap(self, direction: FlexDirection) -> float:
        """Get the gap size for the given flex direction.

        Row direction uses column_gap, column direction uses row_gap.
        Falls back to the general gap property if specific gap is None.
        """
        if direction.is_row():
            return self.column_gap if self.column_gap is not None else self.gap
        return self.row_gap if self.row_gap is not None else self.gap
