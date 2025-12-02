# tests/test_computed.py
"""Tests for Computed - memoized values that auto-update on signal changes."""

from flow.computed import Computed
from flow.signal import Signal


def test_computed_returns_value():
    """Computed property returns calculated value."""
    a = Signal(2)
    b = Signal(3)

    @Computed
    def sum_ab():
        return a.value + b.value

    assert sum_ab() == 5


def test_computed_caches_result():
    """Computed caches until dependencies change."""
    call_count = 0
    a = Signal(10)

    @Computed
    def expensive():
        nonlocal call_count
        call_count += 1
        return a.value * 2

    # First call computes
    result1 = expensive()
    assert result1 == 20
    assert call_count == 1

    # Second call uses cache
    result2 = expensive()
    assert result2 == 20
    assert call_count == 1  # Not recomputed


def test_computed_invalidates_on_signal_change():
    """Computed re-calculates when signal changes."""
    x = Signal(5)

    @Computed
    def doubled():
        return x.value * 2

    assert doubled() == 10

    x.value = 7
    assert doubled() == 14


def test_computed_tracks_multiple_signals():
    """Computed tracks all signals accessed."""
    a = Signal(1)
    b = Signal(2)
    c = Signal(3)

    @Computed
    def total():
        return a.value + b.value + c.value

    assert total() == 6

    b.value = 10
    assert total() == 14

    c.value = 20
    assert total() == 31
