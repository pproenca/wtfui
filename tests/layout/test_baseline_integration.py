# tests/test_layout_baseline_integration.py
"""Integration tests for baseline alignment in layout computation."""

from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.node import LayoutNode
from wtfui.tui.layout.style import AlignItems, FlexDirection, FlexStyle
from wtfui.tui.layout.types import Dimension, Size


def baseline_80_percent(width: float, height: float) -> float:
    """Baseline function returning 80% of height."""
    return height * 0.8


class TestBaselineAlignmentIntegration:
    """Tests that baseline alignment uses calculate_baseline properly."""

    def test_row_baseline_alignment_with_different_heights(self) -> None:
        """Items with different heights align on their baselines.

        Given three items with heights 20, 40, 60 and baselines at 80% height:
        - Item 1: height=20, baseline=16
        - Item 2: height=40, baseline=32
        - Item 3: height=60, baseline=48

        All baselines should align at y=48 (the max baseline):
        - Item 1: y = 48 - 16 = 32
        - Item 2: y = 48 - 32 = 16
        - Item 3: y = 48 - 48 = 0
        """
        # Create parent with baseline alignment
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
                width=Dimension.points(300),
                height=Dimension.points(100),
            )
        )

        # Create children with baseline_func returning 80% of height
        for height in [20, 40, 60]:
            child = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(50),
                    height=Dimension.points(height),
                ),
                baseline_func=baseline_80_percent,
            )
            parent.add_child(child)

        # Compute layout
        compute_layout(parent, Size(300, 100))

        # Verify baselines are aligned
        # Max baseline = 60 * 0.8 = 48
        children = parent.children

        # Item 1 (h=20): y = 48 - 16 = 32
        assert children[0].layout.y == 32.0, f"Expected y=32, got {children[0].layout.y}"

        # Item 2 (h=40): y = 48 - 32 = 16
        assert children[1].layout.y == 16.0, f"Expected y=16, got {children[1].layout.y}"

        # Item 3 (h=60): y = 48 - 48 = 0
        assert children[2].layout.y == 0.0, f"Expected y=0, got {children[2].layout.y}"

    def test_baseline_from_nested_child(self) -> None:
        """Baseline is calculated recursively from first child.

        Parent without baseline_func should use its first child's baseline.
        This tests the recursive calculate_baseline() behavior.
        """
        # Leaf with baseline_func
        leaf = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(30),
                height=Dimension.points(20),
            ),
            baseline_func=baseline_80_percent,  # baseline = 16
        )

        # Intermediate wrapper (no baseline_func)
        # Without padding, leaf is at y=0 inside wrapper
        wrapper = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                height=Dimension.points(30),
            ),
        )
        wrapper.add_child(leaf)

        # Sibling with its own baseline
        sibling = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                height=Dimension.points(40),
            ),
            baseline_func=baseline_80_percent,  # baseline = 32
        )

        # Parent row with baseline alignment
        parent = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
                width=Dimension.points(200),
                height=Dimension.points(60),
            )
        )
        parent.add_child(wrapper)
        parent.add_child(sibling)

        compute_layout(parent, Size(200, 60))

        # Wrapper has no baseline_func, so should recursively calculate from leaf:
        # - leaf.layout.y (inside wrapper) = 0
        # - leaf baseline = 20 * 0.8 = 16
        # - wrapper baseline = 0 + 16 = 16
        #
        # Sibling's baseline = 40 * 0.8 = 32
        # Max baseline = 32
        #
        # Wrapper: y = 32 - 16 = 16
        # Sibling: y = 32 - 32 = 0
        assert wrapper.layout.y == 16.0, f"Expected y=16, got {wrapper.layout.y}"
        assert sibling.layout.y == 0.0, f"Expected y=0, got {sibling.layout.y}"
