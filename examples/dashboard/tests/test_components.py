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
