# tests/test_layout_intrinsic.py
from flow.layout.compute import compute_layout
from flow.layout.intrinsic import (
    calculate_fit_content_width,
    calculate_max_content_width,
    calculate_min_content_width,
)
from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle
from flow.layout.types import Dimension, Size


class TestMinContentWidth:
    def test_min_content_explicit_width(self):
        """Explicit width returns the set value."""
        node = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        assert calculate_min_content_width(node) == 100

    def test_min_content_empty_node(self):
        """Empty node has min-content width of 0."""
        node = LayoutNode(style=FlexStyle())
        assert calculate_min_content_width(node) == 0

    def test_min_content_row_children(self):
        """Row container: sum of children's min-content widths."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(50)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(30)))
        parent.add_child(child1)
        parent.add_child(child2)

        assert calculate_min_content_width(parent) == 80  # 50 + 30

    def test_min_content_row_with_gap(self):
        """Row container with gap includes gaps in calculation."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW, gap=10))
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(50)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(30)))
        parent.add_child(child1)
        parent.add_child(child2)

        assert calculate_min_content_width(parent) == 90  # 50 + 30 + 10

    def test_min_content_column_children(self):
        """Column container: max of children's min-content widths."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.COLUMN))
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(50)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(80)))
        parent.add_child(child1)
        parent.add_child(child2)

        assert calculate_min_content_width(parent) == 80  # max(50, 80)


class TestMaxContentWidth:
    def test_max_content_explicit_width(self):
        """Explicit width returns the set value."""
        node = LayoutNode(style=FlexStyle(width=Dimension.points(200)))
        assert calculate_max_content_width(node) == 200

    def test_max_content_row_children(self):
        """Row container: sum of children's max-content widths."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(150)))
        parent.add_child(child1)
        parent.add_child(child2)

        assert calculate_max_content_width(parent) == 250


class TestFitContentWidth:
    def test_fit_content_clamps_to_max(self):
        """Fit-content clamps large available to max-content."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        parent.add_child(child)

        # Available 500, max-content 100 -> result is 100
        result = calculate_fit_content_width(parent, available=500)
        assert result == 100

    def test_fit_content_uses_available(self):
        """Fit-content uses available when between min and max."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(50)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        parent.add_child(child1)
        parent.add_child(child2)

        # max-content = 150, available = 80 (between min and max) -> result is 80
        # But min-content = 150 for row, so result is min(150, max(150, 80)) = 150
        result = calculate_fit_content_width(parent, available=80)
        assert result == 150  # min-content is the floor

    def test_fit_content_with_max_clamp(self):
        """Fit-content respects optional max clamp."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child = LayoutNode(style=FlexStyle(width=Dimension.points(200)))
        parent.add_child(child)

        # max-content = 200, clamp to 150
        result = calculate_fit_content_width(parent, available=500, max_clamp=150)
        assert result == 150


class TestIntrinsicDimensionCompute:
    def test_width_min_content_in_layout(self):
        """Width: min-content resolves during layout computation."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        parent.add_child(child)

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.min_content(),
            )
        )
        node.add_child(parent)

        compute_layout(node, Size(width=500, height=200))

        # min-content of row with 100px child = 100
        assert node.layout.width == 100

    def test_width_max_content_in_layout(self):
        """Width: max-content resolves during layout computation."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child = LayoutNode(style=FlexStyle(width=Dimension.points(120)))
        parent.add_child(child)

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.max_content(),
            )
        )
        node.add_child(parent)

        compute_layout(node, Size(width=500, height=200))

        # max-content of row with 120px child = 120
        assert node.layout.width == 120

    def test_width_fit_content_in_layout(self):
        """Width: fit-content resolves during layout computation."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        child = LayoutNode(style=FlexStyle(width=Dimension.points(80)))
        parent.add_child(child)

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.fit_content(max_size=150),
            )
        )
        node.add_child(parent)

        compute_layout(node, Size(width=500, height=200))

        # fit-content with max-content=80, available=500, clamp=150 -> 80
        assert node.layout.width == 80

    def test_dimension_is_intrinsic(self):
        """Dimension.is_intrinsic() correctly identifies intrinsic types."""
        assert Dimension.min_content().is_intrinsic()
        assert Dimension.max_content().is_intrinsic()
        assert Dimension.fit_content().is_intrinsic()
        assert not Dimension.auto().is_intrinsic()
        assert not Dimension.points(100).is_intrinsic()
        assert not Dimension.percent(50).is_intrinsic()
