# tests/test_layout_cache.py
"""Tests for layout caching (Yoga parity)."""

from flow.layout.node import CachedMeasurement, LayoutNode, MeasureMode
from flow.layout.style import FlexStyle


class TestCachedMeasurement:
    """Tests for CachedMeasurement dataclass."""

    def test_cached_measurement_dataclass(self):
        """CachedMeasurement stores sizing parameters and result."""
        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.AT_MOST,
            computed_width=100,
            computed_height=150,
        )
        assert cache.available_width == 100
        assert cache.computed_width == 100

    def test_node_has_cached_measurement(self):
        """LayoutNode can store cached measurement."""
        node = LayoutNode(style=FlexStyle())
        assert node.cached_measurement is None

        node.cached_measurement = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.AT_MOST,
            computed_width=100,
            computed_height=150,
        )
        assert node.cached_measurement is not None
        assert node.cached_measurement.computed_width == 100

    def test_invalidate_cache(self):
        """invalidate_cache clears the cached measurement."""
        node = LayoutNode(style=FlexStyle())
        node.cached_measurement = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.AT_MOST,
            computed_width=100,
            computed_height=150,
        )

        node.invalidate_cache()
        assert node.cached_measurement is None
