from dataclasses import dataclass, field, replace
from enum import Enum

from wtfui.tui.layout.types import Border, Dimension, Spacing


class FlexDirection(Enum):
    ROW = "row"
    COLUMN = "column"
    ROW_REVERSE = "row-reverse"
    COLUMN_REVERSE = "column-reverse"

    def is_row(self) -> bool:
        return self in (FlexDirection.ROW, FlexDirection.ROW_REVERSE)

    def is_column(self) -> bool:
        return self in (FlexDirection.COLUMN, FlexDirection.COLUMN_REVERSE)

    def is_reverse(self) -> bool:
        return self in (FlexDirection.ROW_REVERSE, FlexDirection.COLUMN_REVERSE)


class FlexWrap(Enum):
    NO_WRAP = "nowrap"
    WRAP = "wrap"
    WRAP_REVERSE = "wrap-reverse"

    def is_no_wrap(self) -> bool:
        return self == FlexWrap.NO_WRAP

    def is_wrap(self) -> bool:
        return self in (FlexWrap.WRAP, FlexWrap.WRAP_REVERSE)

    def is_reverse(self) -> bool:
        return self == FlexWrap.WRAP_REVERSE


class JustifyContent(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class AlignItems(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"


class AlignContent(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class Position(Enum):
    STATIC = "static"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"

    def is_static(self) -> bool:
        return self == Position.STATIC

    def is_positioned(self) -> bool:
        return self in (Position.RELATIVE, Position.ABSOLUTE)


class Display(Enum):
    FLEX = "flex"
    NONE = "none"
    CONTENTS = "contents"

    def is_visible(self) -> bool:
        return self != Display.NONE

    def is_contents(self) -> bool:
        return self == Display.CONTENTS


class Direction(Enum):
    INHERIT = "inherit"
    LTR = "ltr"
    RTL = "rtl"

    def is_ltr(self) -> bool:
        return self == Direction.LTR

    def is_rtl(self) -> bool:
        return self == Direction.RTL


class Overflow(Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    SCROLL = "scroll"

    def allows_overflow(self) -> bool:
        return self == Overflow.VISIBLE

    def is_scrollable(self) -> bool:
        return self == Overflow.SCROLL


class BoxSizing(Enum):
    BORDER_BOX = "border-box"
    CONTENT_BOX = "content-box"

    def includes_padding(self) -> bool:
        return self == BoxSizing.BORDER_BOX


@dataclass(frozen=True, slots=True)
class FlexStyle:
    display: Display = Display.FLEX
    position: Position = Position.RELATIVE
    direction: Direction = Direction.INHERIT
    overflow: Overflow = Overflow.VISIBLE
    box_sizing: BoxSizing = BoxSizing.BORDER_BOX

    flex_direction: FlexDirection = FlexDirection.ROW
    flex_wrap: FlexWrap = FlexWrap.NO_WRAP
    justify_content: JustifyContent = JustifyContent.FLEX_START
    align_items: AlignItems = AlignItems.STRETCH
    align_content: AlignContent = AlignContent.STRETCH

    flex_grow: float = 0.0
    flex_shrink: float = 1.0
    flex_basis: Dimension = field(default_factory=Dimension.auto)
    align_self: AlignItems | None = None

    width: Dimension = field(default_factory=Dimension.auto)
    height: Dimension = field(default_factory=Dimension.auto)
    min_width: Dimension = field(default_factory=Dimension.auto)
    min_height: Dimension = field(default_factory=Dimension.auto)
    max_width: Dimension = field(default_factory=Dimension.auto)
    max_height: Dimension = field(default_factory=Dimension.auto)
    aspect_ratio: float | None = None

    margin: Spacing = field(default_factory=Spacing)
    padding: Spacing = field(default_factory=Spacing)
    border: Border = field(default_factory=Border.zero)
    gap: float = 0.0
    row_gap: float | None = None
    column_gap: float | None = None

    top: Dimension = field(default_factory=Dimension.auto)
    right: Dimension = field(default_factory=Dimension.auto)
    bottom: Dimension = field(default_factory=Dimension.auto)
    left: Dimension = field(default_factory=Dimension.auto)

    def with_updates(self, **kwargs: object) -> FlexStyle:
        return replace(self, **kwargs)

    def get_gap(self, direction: FlexDirection) -> float:
        if direction.is_row():
            return self.column_gap if self.column_gap is not None else self.gap
        return self.row_gap if self.row_gap is not None else self.gap
