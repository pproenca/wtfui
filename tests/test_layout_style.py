# tests/test_layout_style.py
from flow.layout.style import (
    AlignContent,
    AlignItems,
    FlexDirection,
    FlexWrap,
    JustifyContent,
    Position,
)


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
