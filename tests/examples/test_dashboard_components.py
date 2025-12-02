"""Tests for dashboard components."""

import pytest

from flow import Computed, Signal


@pytest.mark.asyncio
async def test_metric_card_renders():
    from examples.dashboard.components.metric_card import MetricCard

    value = Signal(100)
    card = await MetricCard(title="Revenue", value=value, unit="$")

    assert card is not None


@pytest.mark.asyncio
async def test_metric_card_with_computed():
    from examples.dashboard.components.metric_card import MetricCard

    data = Signal([10, 20, 30])

    @Computed
    def total() -> int:
        return sum(data.value)

    card = await MetricCard(title="Total", value=total, unit="items")
    assert card is not None
