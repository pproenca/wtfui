# tests/test_layout_baseline.py
"""Tests for baseline alignment (Yoga parity)."""

from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import AlignItems, FlexDirection, FlexStyle
from flow.layout.types import Dimension


class TestBaselineFunc:
    """Tests for BaselineFunc protocol."""

    def test_baseline_func_protocol(self):
        """BaselineFunc takes width/height and returns baseline offset from top."""

        def my_baseline(width: float, height: float) -> float:
            # Typical text baseline: 80% from top (20% descender)
            return height * 0.8

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
            baseline_func=my_baseline,
        )

        assert node.has_baseline_func()
        baseline = node.get_baseline(100, 50)
        assert baseline == 40.0  # 50 * 0.8

    def test_node_without_baseline_func(self):
        """Node without baseline_func returns None."""
        node = LayoutNode(style=FlexStyle())
        assert not node.has_baseline_func()
        assert node.get_baseline(100, 50) is None


class TestCalculateBaseline:
    """Tests for calculate_baseline function."""

    def test_baseline_from_baseline_func(self):
        """Node with baseline_func uses it directly."""
        from flow.layout.baseline import calculate_baseline

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
            baseline_func=lambda w, h: h * 0.8,
        )
        node.layout = LayoutResult(x=0, y=0, width=100, height=50)

        baseline = calculate_baseline(node)
        assert baseline == 40.0

    def test_baseline_from_first_child(self):
        """Node without baseline_func uses first child's baseline."""
        from flow.layout.baseline import calculate_baseline

        child = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)),
            baseline_func=lambda w, h: h * 0.8,  # 24
        )
        child.layout = LayoutResult(x=10, y=5, width=50, height=30)

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
        )
        parent.add_child(child)
        parent.layout = LayoutResult(x=0, y=0, width=100, height=50)

        # Baseline = child.y + child baseline = 5 + 24 = 29
        baseline = calculate_baseline(parent)
        assert baseline == 29.0

    def test_baseline_no_children_uses_height(self):
        """Node without baseline_func or children uses its own height."""
        from flow.layout.baseline import calculate_baseline

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
        )
        node.layout = LayoutResult(x=0, y=0, width=100, height=50)

        baseline = calculate_baseline(node)
        assert baseline == 50.0


class TestIsBaselineLayout:
    """Tests for is_baseline_layout function."""

    def test_row_with_align_baseline(self):
        """Row with align-items: baseline is baseline layout."""
        from flow.layout.baseline import is_baseline_layout

        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            ),
        )
        assert is_baseline_layout(node)

    def test_column_never_baseline(self):
        """Column direction is never baseline layout."""
        from flow.layout.baseline import is_baseline_layout

        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.COLUMN,
                align_items=AlignItems.BASELINE,
            ),
        )
        assert not is_baseline_layout(node)

    def test_row_without_baseline_alignment(self):
        """Row with non-baseline alignment is not baseline layout."""
        from flow.layout.baseline import is_baseline_layout

        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.CENTER,
            ),
        )
        assert not is_baseline_layout(node)
