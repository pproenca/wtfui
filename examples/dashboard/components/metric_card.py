# examples/dashboard/components/metric_card.py
"""MetricCard component for displaying key metrics."""

from typing import overload

from wtfui import Computed, Element, Signal, component
from wtfui.core.style import Colors, Style
from wtfui.ui import Box, Flex, Text

# Type alias for numeric metric values
NumericValue = int | float
MetricValue = Signal[NumericValue] | Computed[NumericValue] | NumericValue


@overload
def resolve_metric_value(value: Signal[NumericValue]) -> NumericValue: ...


@overload
def resolve_metric_value(value: Computed[NumericValue]) -> NumericValue: ...


@overload
def resolve_metric_value(value: int) -> int: ...


@overload
def resolve_metric_value(value: float) -> float: ...


def resolve_metric_value(value: MetricValue) -> NumericValue:
    """Resolve a metric value to its underlying numeric value.

    Handles:
    - Signal: Access .value property
    - Computed: Call to get value
    - int/float: Return as-is
    """
    if isinstance(value, Signal):
        return value.value  # type: ignore[return-value]
    if isinstance(value, Computed):
        return value()  # type: ignore[return-value]
    return value


@component
async def MetricCard(
    title: str,
    value: MetricValue,
    unit: str = "",
    change: float | None = None,
) -> Element:
    """Premium metric card with refined typography and visual hierarchy.

    Args:
        title: Metric name
        value: Current value (Signal, Computed, or static)
        unit: Unit prefix/suffix (e.g., "$", "%", "items")
        change: Optional percentage change (positive = green, negative = red)
    """
    display_value = resolve_metric_value(value)

    with Box(
        padding=20,
        width=240,
        style=Style(
            bg="white",
            rounded="lg",
            shadow="sm",
            border=True,
            border_color=Colors.Slate._100,
        ),
    ) as card:
        Text(
            title,
            style=Style(font_size="sm", color=Colors.Slate._500, font_weight="bold"),
        )

        with Flex(direction="row", align="baseline", gap=2):
            if unit and not unit.endswith("%"):
                Text(
                    unit,
                    style=Style(font_size="xl", color=Colors.Slate._400, font_weight="bold"),
                )
            formatted = (
                f"{display_value:,.0f}" if isinstance(display_value, float) else str(display_value)
            )
            Text(
                formatted,
                style=Style(font_size="3xl", font_weight="bold", color=Colors.Slate._900),
            )
            if unit and unit.endswith("%"):
                Text(
                    unit,
                    style=Style(font_size="xl", color=Colors.Slate._400, font_weight="bold"),
                )

        if change is not None:
            change_color = Colors.Emerald._500 if change >= 0 else Colors.Red._500
            change_bg = Colors.Emerald._50 if change >= 0 else Colors.Red._50
            arrow = "^" if change >= 0 else "v"

            with Box(
                style=Style(mt=12, pt=12, border_top=True, border_color=Colors.Slate._100),
            ):
                with Flex(direction="row", align="center", gap=4):
                    with Box(style=Style(bg=change_bg, rounded="md", px=6, py=2)):
                        Text(
                            f"{arrow} {abs(change):.1f}%",
                            style=Style(font_size="sm", color=change_color, font_weight="bold"),
                        )
                    Text(
                        "vs last period",
                        style=Style(font_size="sm", color=Colors.Slate._400),
                    )

    return card
