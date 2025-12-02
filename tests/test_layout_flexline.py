# tests/test_layout_flexline.py
from flow.layout.flexline import collect_flex_lines
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle, FlexWrap
from flow.layout.types import Dimension


class TestFlexLines:
    def test_no_wrap_single_line(self):
        """No-wrap puts all items in one line."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,  # Less than total (150)
            wrap=FlexWrap.NO_WRAP,
            gap=0,
        )

        assert len(lines) == 1
        assert len(lines[0].items) == 3

    def test_wrap_creates_multiple_lines(self):
        """Wrap creates new line when items overflow."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=0,
        )

        # 60 + 60 > 100, so second item wraps
        assert len(lines) == 3
        assert len(lines[0].items) == 1
        assert len(lines[1].items) == 1
        assert len(lines[2].items) == 1

    def test_wrap_with_gap(self):
        """Gap affects when items wrap."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=20,  # 45 + 20 + 45 > 100
        )

        assert len(lines) == 3

    def test_empty_items(self):
        """Empty items list returns empty result."""
        lines = collect_flex_lines(
            items=[],
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=0,
        )
        assert lines == []

    def test_flex_basis_used_for_sizing(self):
        """Flex-basis is used for determining item size."""
        items = [
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(60))),
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(60))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=0,
        )

        # 60 + 60 > 100, so second item wraps
        assert len(lines) == 2

    def test_items_fit_on_single_line(self):
        """Items that fit stay on one line."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(30))),
            LayoutNode(style=FlexStyle(width=Dimension.points(30))),
            LayoutNode(style=FlexStyle(width=Dimension.points(30))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,  # 30 + 30 + 30 = 90, fits
            wrap=FlexWrap.WRAP,
            gap=0,
        )

        assert len(lines) == 1
        assert len(lines[0].items) == 3
