# tests/test_layout_style.py
import pytest

from flow.layout.style import (
    AlignContent,
    AlignItems,
    FlexDirection,
    FlexStyle,
    FlexWrap,
    JustifyContent,
    Position,
)
from flow.layout.types import Dimension


class TestFlexDirection:
    def test_row_is_horizontal(self):
        assert FlexDirection.ROW.is_row()
        assert not FlexDirection.ROW.is_column()

    def test_column_is_vertical(self):
        assert FlexDirection.COLUMN.is_column()
        assert not FlexDirection.COLUMN.is_row()

    def test_reverse_directions(self):
        assert FlexDirection.ROW_REVERSE.is_reverse()
        assert FlexDirection.COLUMN_REVERSE.is_reverse()
        assert not FlexDirection.ROW.is_reverse()


class TestFlexWrap:
    def test_wrap_modes(self):
        assert FlexWrap.NO_WRAP.is_no_wrap()
        assert FlexWrap.WRAP.is_wrap()
        assert FlexWrap.WRAP_REVERSE.is_wrap()
        assert FlexWrap.WRAP_REVERSE.is_reverse()


class TestJustifyContent:
    def test_all_values_exist(self):
        assert JustifyContent.FLEX_START.value == "flex-start"
        assert JustifyContent.FLEX_END.value == "flex-end"
        assert JustifyContent.CENTER.value == "center"
        assert JustifyContent.SPACE_BETWEEN.value == "space-between"
        assert JustifyContent.SPACE_AROUND.value == "space-around"
        assert JustifyContent.SPACE_EVENLY.value == "space-evenly"


class TestAlignItems:
    def test_all_values_exist(self):
        assert AlignItems.FLEX_START.value == "flex-start"
        assert AlignItems.FLEX_END.value == "flex-end"
        assert AlignItems.CENTER.value == "center"
        assert AlignItems.STRETCH.value == "stretch"
        assert AlignItems.BASELINE.value == "baseline"


class TestAlignContent:
    def test_all_values_exist(self):
        assert AlignContent.FLEX_START.value == "flex-start"
        assert AlignContent.FLEX_END.value == "flex-end"
        assert AlignContent.CENTER.value == "center"
        assert AlignContent.STRETCH.value == "stretch"
        assert AlignContent.SPACE_BETWEEN.value == "space-between"
        assert AlignContent.SPACE_AROUND.value == "space-around"


class TestPosition:
    def test_position_modes(self):
        assert Position.RELATIVE.value == "relative"
        assert Position.ABSOLUTE.value == "absolute"


class TestDisplay:
    def test_display_flex_default(self):
        """Flex is the default display mode."""
        from flow.layout.style import Display

        assert Display.FLEX.value == "flex"
        assert Display.FLEX.is_visible()

    def test_display_none_hidden(self):
        """Display none hides the element."""
        from flow.layout.style import Display

        assert Display.NONE.value == "none"
        assert not Display.NONE.is_visible()

    def test_display_contents(self):
        """Display contents makes element act as if replaced by children."""
        from flow.layout.style import Display

        assert Display.CONTENTS.value == "contents"
        assert Display.CONTENTS.is_visible()
        assert Display.CONTENTS.is_contents()


class TestFlexStyle:
    def test_default_style(self):
        style = FlexStyle()
        assert style.flex_direction == FlexDirection.ROW
        assert style.flex_wrap == FlexWrap.NO_WRAP
        assert style.justify_content == JustifyContent.FLEX_START
        assert style.align_items == AlignItems.STRETCH

    def test_style_with_dimensions(self):
        style = FlexStyle(
            width=Dimension.points(100),
            height=Dimension.percent(50),
            flex_grow=1.0,
            flex_shrink=0.0,
        )
        assert style.width.resolve(200) == 100
        assert style.height.resolve(200) == 100
        assert style.flex_grow == 1.0

    def test_style_immutable(self):
        style = FlexStyle()
        with pytest.raises(AttributeError):  # frozen dataclass
            style.flex_grow = 1.0  # type: ignore[misc]

    def test_style_copy_with(self):
        style = FlexStyle(flex_grow=1.0)
        new_style = style.with_updates(flex_shrink=0.5)
        assert new_style.flex_grow == 1.0
        assert new_style.flex_shrink == 0.5
        assert style.flex_shrink != 0.5  # original unchanged

    def test_get_gap_for_row(self):
        style = FlexStyle(gap=10.0, column_gap=20.0)
        assert style.get_gap(FlexDirection.ROW) == 20.0  # column_gap takes precedence

    def test_get_gap_for_column(self):
        style = FlexStyle(gap=10.0, row_gap=15.0)
        assert style.get_gap(FlexDirection.COLUMN) == 15.0  # row_gap takes precedence

    def test_get_gap_fallback(self):
        style = FlexStyle(gap=10.0)
        assert style.get_gap(FlexDirection.ROW) == 10.0
        assert style.get_gap(FlexDirection.COLUMN) == 10.0
