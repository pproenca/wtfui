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


class TestCanUseCachedMeasurement:
    """Tests for can_use_cached_measurement function."""

    def test_cache_hit_exact_match(self):
        """Cache is usable when parameters match exactly."""
        from flow.layout.cache import can_use_cached_measurement

        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.EXACTLY,
            computed_width=100,
            computed_height=200,
        )

        result = can_use_cached_measurement(
            cache=cache,
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.EXACTLY,
        )
        assert result is True

    def test_cache_miss_different_width(self):
        """Cache is not usable when width differs."""
        from flow.layout.cache import can_use_cached_measurement

        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.EXACTLY,
            computed_width=100,
            computed_height=200,
        )

        result = can_use_cached_measurement(
            cache=cache,
            available_width=150,  # Different
            available_height=200,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.EXACTLY,
        )
        assert result is False

    def test_cache_hit_at_most_fits(self):
        """Cache is usable when AT_MOST constraint is satisfied."""
        from flow.layout.cache import can_use_cached_measurement

        # Previously computed with AT_MOST 100, result was 80
        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.AT_MOST,
            height_mode=MeasureMode.EXACTLY,
            computed_width=80,  # Fits within constraint
            computed_height=200,
        )

        # New request with larger AT_MOST should still be valid
        result = can_use_cached_measurement(
            cache=cache,
            available_width=120,  # Larger constraint
            available_height=200,
            width_mode=MeasureMode.AT_MOST,
            height_mode=MeasureMode.EXACTLY,
        )
        assert result is True

    def test_cache_miss_at_most_would_overflow(self):
        """Cache is not usable when smaller AT_MOST would overflow."""
        from flow.layout.cache import can_use_cached_measurement

        # Previously computed with AT_MOST 100, result was 100 (used all space)
        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=MeasureMode.AT_MOST,
            height_mode=MeasureMode.EXACTLY,
            computed_width=100,  # Used all available space
            computed_height=200,
        )

        # Smaller constraint might produce different result
        result = can_use_cached_measurement(
            cache=cache,
            available_width=80,  # Smaller constraint
            available_height=200,
            width_mode=MeasureMode.AT_MOST,
            height_mode=MeasureMode.EXACTLY,
        )
        assert result is False

    def test_cache_hit_undefined_no_constraint(self):
        """Cache with UNDEFINED mode is reusable when mode matches."""
        from flow.layout.cache import can_use_cached_measurement

        cache = CachedMeasurement(
            available_width=0,
            available_height=0,
            width_mode=MeasureMode.UNDEFINED,
            height_mode=MeasureMode.UNDEFINED,
            computed_width=50,
            computed_height=30,
        )

        result = can_use_cached_measurement(
            cache=cache,
            available_width=0,
            available_height=0,
            width_mode=MeasureMode.UNDEFINED,
            height_mode=MeasureMode.UNDEFINED,
        )
        assert result is True
