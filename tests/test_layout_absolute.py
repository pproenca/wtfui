# tests/test_layout_absolute.py
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle, Position
from flow.layout.types import Dimension, Size


class TestAbsolutePositioning:
    def test_absolute_child_removed_from_flex_flow(self):
        """Absolute children don't participate in flex layout."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        # Relative child takes up space
        rel = LayoutNode(style=FlexStyle(width=Dimension.points(50), flex_grow=1))
        parent.add_child(rel)

        # Absolute child doesn't take up space
        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        # Relative child should take all available space (flex_grow=1)
        assert rel.layout.width == 200

    def test_absolute_with_top_left_insets(self):
        """Absolute child positioned with top/left insets."""
        parent = LayoutNode(style=FlexStyle())

        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                top=Dimension.points(20),
                left=Dimension.points(30),
                width=Dimension.points(50),
                height=Dimension.points(40),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        assert abs_child.layout.x == 30
        assert abs_child.layout.y == 20
        assert abs_child.layout.width == 50
        assert abs_child.layout.height == 40

    def test_absolute_with_right_bottom_insets(self):
        """Absolute child positioned with right/bottom insets."""
        parent = LayoutNode(style=FlexStyle())

        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                right=Dimension.points(20),
                bottom=Dimension.points(10),
                width=Dimension.points(50),
                height=Dimension.points(40),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        # Right: 200 - 20 - 50 = 130
        # Bottom: 100 - 10 - 40 = 50
        assert abs_child.layout.x == 130
        assert abs_child.layout.y == 50

    def test_absolute_with_all_insets_stretches(self):
        """Absolute child with all insets stretches to fill."""
        parent = LayoutNode(style=FlexStyle())

        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                top=Dimension.points(10),
                right=Dimension.points(20),
                bottom=Dimension.points(10),
                left=Dimension.points(20),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        # Width: 200 - 20 - 20 = 160
        # Height: 100 - 10 - 10 = 80
        assert abs_child.layout.x == 20
        assert abs_child.layout.y == 10
        assert abs_child.layout.width == 160
        assert abs_child.layout.height == 80

    def test_absolute_percent_insets(self):
        """Absolute child with percentage insets."""
        parent = LayoutNode(style=FlexStyle())

        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                top=Dimension.percent(10),  # 10% of 100 = 10
                left=Dimension.percent(25),  # 25% of 200 = 50
                width=Dimension.points(50),
                height=Dimension.points(30),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        assert abs_child.layout.x == 50
        assert abs_child.layout.y == 10

    def test_mixed_relative_and_absolute_children(self):
        """Container with both relative and absolute children."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        # Two relative children
        rel1 = LayoutNode(style=FlexStyle(flex_grow=1))
        rel2 = LayoutNode(style=FlexStyle(flex_grow=1))

        # One absolute child
        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                top=Dimension.points(0),
                left=Dimension.points(0),
                width=Dimension.points(50),
                height=Dimension.points(50),
            )
        )

        parent.add_child(rel1)
        parent.add_child(abs_child)  # Order doesn't matter for absolute
        parent.add_child(rel2)

        compute_layout(parent, Size(width=200, height=100))

        # Relative children split the space
        assert rel1.layout.width == 100
        assert rel2.layout.width == 100

        # Absolute child positioned separately
        assert abs_child.layout.x == 0
        assert abs_child.layout.y == 0
        assert abs_child.layout.width == 50

    def test_absolute_defaults_to_top_left(self):
        """Absolute child without insets defaults to top-left (0, 0)."""
        parent = LayoutNode(style=FlexStyle())

        abs_child = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                width=Dimension.points(50),
                height=Dimension.points(50),
            )
        )
        parent.add_child(abs_child)

        compute_layout(parent, Size(width=200, height=100))

        assert abs_child.layout.x == 0
        assert abs_child.layout.y == 0

    def test_nested_absolute_positioning(self):
        """Nested absolute positioning relative to containing block."""
        outer = LayoutNode(style=FlexStyle())

        inner = LayoutNode(style=FlexStyle(flex_grow=1))

        # Absolute grandchild - positioned relative to inner
        abs_grandchild = LayoutNode(
            style=FlexStyle(
                position=Position.ABSOLUTE,
                top=Dimension.points(10),
                left=Dimension.points(10),
                width=Dimension.points(30),
                height=Dimension.points(30),
            )
        )

        outer.add_child(inner)
        inner.add_child(abs_grandchild)

        compute_layout(outer, Size(width=200, height=100))

        # Grandchild relative to inner (which is at 0,0 with full size)
        assert abs_grandchild.layout.x == 10
        assert abs_grandchild.layout.y == 10
