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


class TestBaselineAlignment:
    """Tests for baseline alignment in compute_layout."""

    def test_baseline_alignment_row(self):
        """Items with baseline alignment align on their baselines."""
        from flow.layout.compute import compute_layout
        from flow.layout.types import Size

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            )
        )

        # Small text (baseline at 80% of height)
        small_text = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(20)),
            baseline_func=lambda w, h: h * 0.8,  # baseline at 16
        )

        # Large text (baseline at 80% of height)
        large_text = LayoutNode(
            style=FlexStyle(width=Dimension.points(100), height=Dimension.points(40)),
            baseline_func=lambda w, h: h * 0.8,  # baseline at 32
        )

        parent.add_child(small_text)
        parent.add_child(large_text)

        compute_layout(parent, Size(300, 100))

        # Both baselines should align
        # Large text baseline = y + 32
        # Small text baseline = y + 16
        # For baselines to align: small_y + 16 = large_y + 32
        # If large_text.y = 0, then small_text.y = 16

        small_baseline = small_text.layout.y + 16
        large_baseline = large_text.layout.y + 32

        assert abs(small_baseline - large_baseline) < 0.01

    def test_baseline_with_align_self_override(self):
        """Child with align-self overrides parent's baseline alignment."""
        from flow.layout.compute import compute_layout
        from flow.layout.types import Size

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            )
        )

        # Tall child with baseline at 80% (32px from top)
        baseline_child = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(40)),
            baseline_func=lambda w, h: h * 0.8,  # baseline at 32
        )

        # Short child with center alignment (should be centered within line)
        centered_child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                height=Dimension.points(20),
                align_self=AlignItems.CENTER,  # Override
            ),
        )

        parent.add_child(baseline_child)
        parent.add_child(centered_child)

        compute_layout(parent, Size(200, 100))

        # Line height is determined by tallest child = 40
        # baseline_child has baseline at 32, no offset needed
        # centered_child should be centered in line: (40 - 20) / 2 = 10
        assert baseline_child.layout.y == 0
        assert abs(centered_child.layout.y - 10) < 0.01
