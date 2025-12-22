"""Tests for dashboard components."""

import inspect

import pytest

from wtfui import Computed, Signal


@pytest.mark.asyncio
async def test_metric_card_renders():
    from components.metric_card import MetricCard

    value = Signal(100)
    card = await MetricCard(title="Revenue", value=value, unit="$")

    assert card is not None


@pytest.mark.asyncio
async def test_metric_card_with_computed():
    from components.metric_card import MetricCard

    data = Signal([10, 20, 30])

    @Computed
    def total() -> int:
        return sum(data.value)

    card = await MetricCard(title="Total", value=total, unit="items")
    assert card is not None


@pytest.mark.asyncio
async def test_metric_card_with_callable():
    """Verify MetricCard works with a plain callable (Computed)."""
    from components.metric_card import MetricCard

    @Computed
    def dynamic_value() -> int:
        return 42

    card = await MetricCard(title="Dynamic", value=dynamic_value, unit="items")
    assert card is not None


@pytest.mark.asyncio
async def test_metric_card_with_static_value():
    """Verify MetricCard works with a plain static value."""
    from components.metric_card import MetricCard

    card = await MetricCard(title="Static", value=123, unit="$")
    assert card is not None


@pytest.mark.asyncio
async def test_metric_card_type_union():
    """Verify MetricCard type annotation accepts all valid types."""
    from components.metric_card import MetricCard

    sig = inspect.signature(MetricCard)
    value_param = sig.parameters["value"]

    # Should have MetricValue type alias which includes Signal and Computed
    annotation_str = str(value_param.annotation)
    # Either shows expanded type or type alias name
    assert "MetricValue" in annotation_str or (
        "Signal" in annotation_str and "Computed" in annotation_str
    )


def test_sales_trend_handles_zero_values():
    """Sales trend should not crash with zero values (division by zero)."""
    import app

    # Set sales data to all zeros (simulates multiplier of 0%)
    app._sales_data.value = [0, 0, 0, 0, 0, 0, 0]

    # This should not raise ZeroDivisionError
    result = app._sales_trend()

    # Should return 0.0 when previous value is 0
    assert result == 0.0


def test_sales_trend_normal_calculation():
    """Sales trend calculates week-over-week change correctly."""
    import app

    # Set sales data with known values
    app._sales_data.value = [100, 100, 100, 100, 100, 100, 120]

    result = app._sales_trend()

    # (120 - 100) / 100 * 100 = 20%
    assert result == 20.0


def test_update_multiplier_with_zero():
    """Update multiplier with 0 should not crash."""
    import app

    # Reset to baseline first
    app._sales_data.value = [120, 150, 180, 200, 175, 220, 250]

    # This should not raise
    app.update_multiplier("0")

    # All values should be 0
    assert app._sales_data.value == [0, 0, 0, 0, 0, 0, 0]

    # And sales_trend should not crash
    result = app._sales_trend()
    assert result == 0.0
