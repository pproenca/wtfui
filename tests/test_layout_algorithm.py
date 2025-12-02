# tests/test_layout_algorithm.py
from flow.layout.algorithm import (
    AvailableSpace,
    SizingMode,
    distribute_justify_content,
    resolve_flexible_lengths,
)
from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle, JustifyContent
from flow.layout.types import Dimension


class TestAvailableSpace:
    def test_definite_space(self):
        space = AvailableSpace.definite(100)
        assert space.is_definite()
        assert space.value == 100

    def test_min_content(self):
        space = AvailableSpace.min_content()
        assert space.is_min_content()

    def test_max_content(self):
        space = AvailableSpace.max_content()
        assert space.is_max_content()

    def test_resolve_definite(self):
        space = AvailableSpace.definite(200)
        assert space.resolve() == 200

    def test_resolve_min_content(self):
        space = AvailableSpace.min_content()
        assert space.resolve() == 0

    def test_resolve_max_content(self):
        space = AvailableSpace.max_content()
        assert space.resolve() == float("inf")


class TestSizingMode:
    def test_sizing_modes(self):
        assert SizingMode.CONTENT_BOX.is_content_box()
        assert SizingMode.BORDER_BOX.is_border_box()


class TestResolveFlexibleLengths:
    def test_equal_flex_grow(self):
        """Two items with flex-grow: 1 split space equally."""
        items = [
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=0,
        )

        assert sizes[0] == 100
        assert sizes[1] == 100

    def test_weighted_flex_grow(self):
        """Items with flex-grow 1:2 ratio."""
        items = [
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_grow=2.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=300,
            direction=FlexDirection.ROW,
            gap=0,
        )

        assert sizes[0] == 100  # 1/3 of 300
        assert sizes[1] == 200  # 2/3 of 300

    def test_flex_basis_respected(self):
        """Flex-basis sets initial size before grow/shrink."""
        items = [
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=1.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=0,
        )

        # 200 total - 100 (basis) = 100 free space, split equally
        assert sizes[0] == 100  # 50 basis + 50 grown
        assert sizes[1] == 100  # 50 basis + 50 grown

    def test_flex_shrink(self):
        """Items shrink when container is too small."""
        items = [
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(100), flex_shrink=1.0)),
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(100), flex_shrink=1.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=150,
            direction=FlexDirection.ROW,
            gap=0,
        )

        # 200 total basis - 150 container = 50 to shrink
        # Equal shrink factors and basis, so each shrinks by 25
        assert sizes[0] == 75
        assert sizes[1] == 75

    def test_gap_reduces_available_space(self):
        """Gap between items reduces available space for growing."""
        items = [
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=20,  # 20px gap between items
        )

        # 200 - 20 gap = 180 available, split equally
        assert sizes[0] == 90
        assert sizes[1] == 90

    def test_empty_items(self):
        """Empty items list returns empty result."""
        sizes = resolve_flexible_lengths(
            items=[],
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=0,
        )
        assert sizes == []

    def test_no_flex_grow(self):
        """Items without flex-grow keep their basis."""
        items = [
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=0.0)),
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=0.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=0,
        )

        assert sizes[0] == 50
        assert sizes[1] == 50


class TestJustifyContent:
    def test_flex_start(self):
        """Items align to start with no gaps."""
        positions = distribute_justify_content(
            item_sizes=[50, 50, 50],
            container_size=300,
            justify=JustifyContent.FLEX_START,
            gap=0,
        )
        assert positions == [0, 50, 100]

    def test_flex_end(self):
        """Items align to end."""
        positions = distribute_justify_content(
            item_sizes=[50, 50, 50],
            container_size=300,
            justify=JustifyContent.FLEX_END,
            gap=0,
        )
        assert positions == [150, 200, 250]

    def test_center(self):
        """Items centered in container."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.CENTER,
            gap=0,
        )
        assert positions == [50, 100]  # 50px on each side

    def test_space_between(self):
        """Space distributed between items."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.SPACE_BETWEEN,
            gap=0,
        )
        assert positions == [0, 150]

    def test_space_around(self):
        """Equal space around each item."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.SPACE_AROUND,
            gap=0,
        )
        # 100px free space, 2 items = 25px per side per item
        assert positions == [25, 125]

    def test_space_evenly(self):
        """Equal space between items and edges."""
        positions = distribute_justify_content(
            item_sizes=[40, 40, 40],
            container_size=200,
            justify=JustifyContent.SPACE_EVENLY,
            gap=0,
        )
        # 80px free space, 4 gaps = 20px each
        assert positions == [20, 80, 140]

    def test_with_gap(self):
        """Gap affects free space calculation."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.FLEX_START,
            gap=20,
        )
        # Items at 0 and 50+20=70
        assert positions == [0, 70]

    def test_empty_items(self):
        """Empty items list returns empty result."""
        positions = distribute_justify_content(
            item_sizes=[],
            container_size=200,
            justify=JustifyContent.CENTER,
            gap=0,
        )
        assert positions == []
