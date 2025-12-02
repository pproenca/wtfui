# examples/dashboard/components/metric_card.py
"""MetricCard component for displaying key metrics."""

from __future__ import annotations

from typing import Any

from flow import Computed, Element, Signal, component
from flow.ui import Box, Flex, Text


@component
async def MetricCard(
    title: str,
    value: Signal[int | float] | Computed[int | float] | int | float,
    unit: str = "",
    change: float | None = None,
) -> Element:
    """A card displaying a metric with optional change indicator.

    Args:
        title: Metric name
        value: Current value (Signal, Computed, or static)
        unit: Unit prefix/suffix (e.g., "$", "%", "items")
        change: Optional percentage change (positive = green, negative = red)
    """
    # Resolve value if it's reactive
    display_value: Any
    if callable(value):
        display_value = value()
    elif hasattr(value, "value"):
        display_value = value.value
    else:
        display_value = value

    with Box(
        padding=16,
        width=200,
        cls="bg-white rounded-lg shadow",
    ) as card:
        with Text(title, cls="text-sm text-gray-500"):
            pass

        with Flex(direction="row", align="baseline", gap=4):
            if unit and not unit.endswith("%"):
                with Text(unit, cls="text-lg"):
                    pass
            formatted = (
                f"{display_value:,.0f}" if isinstance(display_value, float) else str(display_value)
            )
            with Text(formatted, cls="text-3xl font-bold"):
                pass
            if unit and unit.endswith("%"):
                with Text(unit, cls="text-lg"):
                    pass

        if change is not None:
            color = "text-green-500" if change >= 0 else "text-red-500"
            arrow = "^" if change >= 0 else "v"
            with Text(f"{arrow} {abs(change):.1f}%", cls=f"text-sm {color}"):
                pass

    return card
