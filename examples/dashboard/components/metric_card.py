# examples/dashboard/components/metric_card.py
"""MetricCard component - Art Deco Geometric Luxury theme."""

from typing import overload

from wtfui import Computed, Element, Signal, component
from wtfui.ui import Flex, Text

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
    """Art Deco luxury metric card with dark glass effect and gold accents.

    Args:
        title: Metric name
        value: Current value (Signal, Computed, or static)
        unit: Unit prefix/suffix (e.g., "$", "%", "items")
        change: Optional percentage change (positive = green, negative = red)
    """
    display_value = resolve_metric_value(value)

    with Flex(
        direction="column",
        cls=(
            "w-60 bg-slate-800/50 backdrop-blur border border-slate-700 "
            "rounded-lg overflow-hidden "
            "hover:border-amber-500/50 transition-all duration-300"
        ),
    ) as card:
        # Gold accent bar at top (geometric Art Deco element)
        Flex(
            direction="row",
            cls="h-1 w-full bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600",
        )

        # Card content
        with Flex(direction="column", cls="p-5 space-y-3"):
            # Title
            with Flex(direction="row"):
                Text(
                    title.upper(),
                    cls="text-xs font-bold tracking-widest text-amber-500/70",
                )

            # Value display
            with Flex(direction="row", cls="items-baseline gap-1"):
                if unit and not unit.endswith("%"):
                    with Flex(direction="row"):
                        Text(unit, cls="text-xl font-bold text-slate-500")
                formatted = (
                    f"{display_value:,.0f}"
                    if isinstance(display_value, float)
                    else str(display_value)
                )
                with Flex(direction="row"):
                    Text(formatted, cls="text-3xl font-bold text-slate-100 tabular-nums")
                if unit and unit.endswith("%"):
                    with Flex(direction="row"):
                        Text(unit, cls="text-xl font-bold text-slate-500")

            # Change indicator
            if change is not None:
                is_positive = change >= 0
                arrow = "^" if is_positive else "v"

                change_cls = (
                    "text-emerald-400 bg-emerald-500/10"
                    if is_positive
                    else "text-red-400 bg-red-500/10"
                )

                with Flex(
                    direction="row",
                    cls="pt-3 mt-2 border-t border-slate-700/50 items-center gap-3",
                ):
                    with Flex(direction="row", cls=f"px-2 py-1 rounded {change_cls}"):
                        Text(
                            f"{arrow} {abs(change):.1f}%",
                            cls="text-xs font-bold",
                        )
                    with Flex(direction="row"):
                        Text("vs last period", cls="text-xs text-slate-500")

    return card
