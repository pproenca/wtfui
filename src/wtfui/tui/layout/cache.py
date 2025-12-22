from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.layout.node import CachedMeasurement, MeasureMode

CACHE_EPSILON = 0.0001


def can_use_cached_measurement(
    cache: CachedMeasurement,
    available_width: float,
    available_height: float,
    width_mode: MeasureMode,
    height_mode: MeasureMode,
) -> bool:
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
    from wtfui.tui.layout.node import MeasureMode

    if cached_mode != new_mode:
        return False

    if new_mode == MeasureMode.EXACTLY:
        return abs(cached_available - new_available) < CACHE_EPSILON

    elif new_mode == MeasureMode.AT_MOST:
        if new_available >= cached_available - CACHE_EPSILON:
            return True
        else:
            return cached_computed <= new_available + CACHE_EPSILON

    elif new_mode == MeasureMode.UNDEFINED:
        return True

    return False
