# src/flow/layout/cache.py
"""Layout caching utilities (matches Yoga's caching logic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import CachedMeasurement, MeasureMode


# Tolerance for floating point comparisons in cache lookups
CACHE_EPSILON = 0.0001


def can_use_cached_measurement(
    cache: CachedMeasurement,
    available_width: float,
    available_height: float,
    width_mode: MeasureMode,
    height_mode: MeasureMode,
) -> bool:
    """Check if a cached measurement can be reused for given constraints.

    This implements Yoga's cache lookup logic from YGCachedMeasurement.
    A cached result is valid if:
    - For EXACTLY mode: the available space matches exactly
    - For AT_MOST mode: the computed size fits within the new constraint
    - For UNDEFINED mode: any value is acceptable

    Args:
        cache: The cached measurement to check.
        available_width: New available width.
        available_height: New available height.
        width_mode: New width sizing mode.
        height_mode: New height sizing mode.

    Returns:
        True if the cached measurement can be reused.
    """

    width_ok = _dimension_matches(
        cached_mode=cache.width_mode,
        cached_available=cache.available_width,
        cached_computed=cache.computed_width,
        new_mode=width_mode,
        new_available=available_width,
    )

    height_ok = _dimension_matches(
        cached_mode=cache.height_mode,
        cached_available=cache.available_height,
        cached_computed=cache.computed_height,
        new_mode=height_mode,
        new_available=available_height,
    )

    return width_ok and height_ok


def _dimension_matches(
    cached_mode: MeasureMode,
    cached_available: float,
    cached_computed: float,
    new_mode: MeasureMode,
    new_available: float,
) -> bool:
    """Check if a single dimension matches for cache reuse.

    Args:
        cached_mode: The mode from the cached measurement.
        cached_available: The available space from the cached measurement.
        cached_computed: The computed size from the cached measurement.
        new_mode: The new requested mode.
        new_available: The new available space.

    Returns:
        True if this dimension can use the cached result.
    """
    from flow.layout.node import MeasureMode

    # Mode must match
    if cached_mode != new_mode:
        return False

    if new_mode == MeasureMode.EXACTLY:
        # For exact mode, available space must match exactly
        return abs(cached_available - new_available) < CACHE_EPSILON

    elif new_mode == MeasureMode.AT_MOST:
        # For at-most mode, cached result is valid if:
        # - New constraint is >= old constraint, OR
        # - Computed size fits within new (smaller) constraint
        if new_available >= cached_available - CACHE_EPSILON:
            # Constraint is same or larger, cached result is valid
            return True
        else:
            # Constraint is smaller - only valid if computed size fits
            return cached_computed <= new_available + CACHE_EPSILON

    elif new_mode == MeasureMode.UNDEFINED:
        # For undefined mode, any value works (intrinsic sizing)
        return True

    return False
