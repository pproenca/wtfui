# tests/test_layout_align_content.py
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import AlignContent, FlexDirection, FlexStyle, FlexWrap
from flow.layout.types import Dimension, Size


class TestAlignContent:
    def test_align_content_flex_start(self):
        """Align-content: flex-start packs lines at the start."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.FLEX_START,
            )
        )

        # Two children that will wrap (each 60px in 100px container)
        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Both lines should be at the top
        assert child1.layout.y == 0
        assert child2.layout.y == 30  # Second line starts at 30

    def test_align_content_flex_end(self):
        """Align-content: flex-end packs lines at the end."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.FLEX_END,
            )
        )

        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Lines packed at bottom: 100 - 60 = 40 offset
        assert child1.layout.y == 40
        assert child2.layout.y == 70

    def test_align_content_center(self):
        """Align-content: center centers lines."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.CENTER,
            )
        )

        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Lines centered: (100 - 60) / 2 = 20 offset
        assert child1.layout.y == 20
        assert child2.layout.y == 50

    def test_align_content_space_between(self):
        """Align-content: space-between distributes space between lines."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.SPACE_BETWEEN,
            )
        )

        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # First line at top, last line at bottom
        assert child1.layout.y == 0
        assert child2.layout.y == 70  # 100 - 30 = 70

    def test_align_content_space_around(self):
        """Align-content: space-around distributes space around lines."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.SPACE_AROUND,
            )
        )

        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Remaining space: 100 - 60 = 40, divided into 4 half-spaces of 10 each
        # First line: 10 offset
        # Second line: 10 + 30 + 20 = 60
        assert child1.layout.y == 10
        assert child2.layout.y == 60

    def test_align_content_stretch(self):
        """Align-content: stretch expands lines to fill container."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.STRETCH,
            )
        )

        # Two children that will wrap
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(60)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(60)))
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Each line gets 50px height (100 / 2)
        assert child1.layout.height == 50
        assert child2.layout.height == 50
        assert child1.layout.y == 0
        assert child2.layout.y == 50

    def test_align_content_space_evenly(self):
        """Align-content: space-evenly distributes space evenly including edges."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.SPACE_EVENLY,
            )
        )

        child1 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        child2 = LayoutNode(
            style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30))
        )
        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(width=100, height=100))

        # Remaining space: 100 - 60 = 40, divided into 3 equal gaps (before, between, after)
        # Each gap: 40 / 3 ≈ 13.33
        # First line: 13.33 offset
        # Second line: 13.33 + 30 + 13.33 = 56.66
        assert abs(child1.layout.y - 13.333) < 0.1
        assert abs(child2.layout.y - 56.666) < 0.1

    def test_align_content_space_evenly_single_line(self):
        """Align-content: space-evenly with single line centers it."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.WRAP,
                align_content=AlignContent.SPACE_EVENLY,
            )
        )

        child = LayoutNode(style=FlexStyle(width=Dimension.points(60), height=Dimension.points(30)))
        parent.add_child(child)

        compute_layout(parent, Size(width=100, height=100))

        # Single line with space-evenly: 2 gaps (before and after)
        # Remaining: 100 - 30 = 70, each gap: 70 / 2 = 35
        assert abs(child.layout.y - 35) < 0.1

    def test_align_content_no_effect_single_line(self):
        """Align-content has no effect on single-line containers."""
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                flex_wrap=FlexWrap.NO_WRAP,  # Single line
                align_content=AlignContent.CENTER,
            )
        )

        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)))
        parent.add_child(child)

        compute_layout(parent, Size(width=100, height=100))

        # Single line, align-content doesn't apply
        assert child.layout.y == 0
