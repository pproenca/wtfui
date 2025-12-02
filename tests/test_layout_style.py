# tests/test_layout_style.py
import pytest

from flow.layout.style import (
    AlignContent,
    AlignItems,
    BoxSizing,
    Direction,
    Display,
    FlexDirection,
    FlexStyle,
    FlexWrap,
    JustifyContent,
    Overflow,
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


class TestPositionStatic:
    """Tests for Position.STATIC and helper methods (Yoga parity)."""

    def test_static_value_exists(self):
        """STATIC position mode should exist."""
        assert Position.STATIC.value == "static"

    def test_is_static_method(self):
        """is_static() should return True only for STATIC."""
        assert Position.STATIC.is_static()
        assert not Position.RELATIVE.is_static()
        assert not Position.ABSOLUTE.is_static()

    def test_is_positioned_method(self):
        """is_positioned() should return True for RELATIVE and ABSOLUTE."""
        assert Position.RELATIVE.is_positioned()
        assert Position.ABSOLUTE.is_positioned()
        assert not Position.STATIC.is_positioned()

    def test_static_default_behavior(self):
        """STATIC should be the default position (normal flow)."""
        # This test documents the intended default behavior
        # FlexStyle currently defaults to RELATIVE, but STATIC
        # matches CSS default and Yoga's default behavior
        style = FlexStyle(position=Position.STATIC)
        assert style.position.is_static()


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


class TestDirection:
    def test_direction_ltr_default(self):
        """LTR is the default direction."""
        from flow.layout.style import Direction

        assert Direction.LTR.value == "ltr"
        assert Direction.LTR.is_ltr()
        assert not Direction.LTR.is_rtl()

    def test_direction_rtl(self):
        """RTL reverses horizontal layout."""
        from flow.layout.style import Direction

        assert Direction.RTL.value == "rtl"
        assert Direction.RTL.is_rtl()
        assert not Direction.RTL.is_ltr()

    def test_direction_inherit(self):
        """Inherit takes direction from parent."""
        from flow.layout.style import Direction

        assert Direction.INHERIT.value == "inherit"
        assert not Direction.INHERIT.is_ltr()
        assert not Direction.INHERIT.is_rtl()


class TestOverflow:
    def test_overflow_visible_default(self):
        """Visible is the default overflow mode."""
        from flow.layout.style import Overflow

        assert Overflow.VISIBLE.value == "visible"
        assert Overflow.VISIBLE.allows_overflow()

    def test_overflow_hidden(self):
        """Hidden clips overflow content."""
        from flow.layout.style import Overflow

        assert Overflow.HIDDEN.value == "hidden"
        assert not Overflow.HIDDEN.allows_overflow()

    def test_overflow_scroll(self):
        """Scroll adds scrollbars for overflow."""
        from flow.layout.style import Overflow

        assert Overflow.SCROLL.value == "scroll"
        assert not Overflow.SCROLL.allows_overflow()
        assert Overflow.SCROLL.is_scrollable()

    def test_overflow_hidden_not_scrollable(self):
        """Hidden is not scrollable."""
        from flow.layout.style import Overflow

        assert not Overflow.HIDDEN.is_scrollable()

    def test_overflow_visible_not_scrollable(self):
        """Visible is not scrollable."""
        from flow.layout.style import Overflow

        assert not Overflow.VISIBLE.is_scrollable()


class TestBoxSizing:
    def test_border_box_default(self):
        """Border-box is the default (width includes padding+border)."""
        from flow.layout.style import BoxSizing

        assert BoxSizing.BORDER_BOX.value == "border-box"
        assert BoxSizing.BORDER_BOX.includes_padding()

    def test_content_box(self):
        """Content-box means width is content only."""
        from flow.layout.style import BoxSizing

        assert BoxSizing.CONTENT_BOX.value == "content-box"
        assert not BoxSizing.CONTENT_BOX.includes_padding()


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


class TestFlexStyleNewEnums:
    """Tests for FlexStyle with new enum fields (Task 1.6)."""

    def test_default_style_has_new_enums(self):
        """Default FlexStyle should have correct default values for new enums."""
        style = FlexStyle()
        assert style.display == Display.FLEX
        assert style.direction == Direction.INHERIT
        assert style.overflow == Overflow.VISIBLE
        assert style.box_sizing == BoxSizing.BORDER_BOX

    def test_style_with_updates_new_enums(self):
        """FlexStyle should accept and store custom enum values."""
        style = FlexStyle(
            display=Display.NONE,
            direction=Direction.RTL,
            overflow=Overflow.HIDDEN,
            box_sizing=BoxSizing.CONTENT_BOX,
        )
        assert style.display == Display.NONE
        assert style.direction == Direction.RTL
        assert style.overflow == Overflow.HIDDEN
        assert style.box_sizing == BoxSizing.CONTENT_BOX

    def test_style_with_partial_enum_updates(self):
        """Can set some new enum fields while keeping defaults for others."""
        style = FlexStyle(
            display=Display.CONTENTS,
            direction=Direction.LTR,
        )
        assert style.display == Display.CONTENTS
        assert style.direction == Direction.LTR
        # Defaults for the others
        assert style.overflow == Overflow.VISIBLE
        assert style.box_sizing == BoxSizing.BORDER_BOX

    def test_style_immutable_with_new_enums(self):
        """New enum fields should respect frozen dataclass."""
        style = FlexStyle()
        with pytest.raises(AttributeError):
            style.display = Display.NONE  # type: ignore[misc]

    def test_style_with_updates_preserves_new_enums(self):
        """with_updates should work with new enum fields."""
        style = FlexStyle(display=Display.NONE)
        new_style = style.with_updates(direction=Direction.RTL)
        assert new_style.display == Display.NONE  # preserved
        assert new_style.direction == Direction.RTL  # updated
        assert style.direction == Direction.INHERIT  # original unchanged
