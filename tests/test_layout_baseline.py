# tests/test_layout_baseline.py
"""Tests for baseline alignment (Yoga parity)."""

from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle
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
