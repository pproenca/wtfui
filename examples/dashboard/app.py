# examples/dashboard/app.py
"""Dashboard - Demonstrates Flexbox layout and Computed values.

This example showcases:
- Flex/Box layout (CSS Flexbox)
- Computed for derived values
- Responsive sizing (flex_grow)
- Component composition

Run with: uv run python examples/dashboard/app.py
"""

from __future__ import annotations

from flow import Computed, Element, Signal, component
from flow.server import create_app
from flow.ui import Box, Flex, Input, Text, VStack

from .components import MetricCard, Sidebar

# Sample data
sales_data: Signal[list[int]] = Signal([120, 150, 180, 200, 175, 220, 250])
user_count: Signal[int] = Signal(1234)
conversion_rate: Signal[float] = Signal(3.2)


# Computed values - automatically update when dependencies change
@Computed
def total_sales() -> int:
    return sum(sales_data.value)


@Computed
def average_sales() -> float:
    data = sales_data.value
    return sum(data) / len(data) if data else 0.0


@Computed
def sales_trend() -> float:
    """Calculate week-over-week change."""
    data = sales_data.value
    if len(data) < 2:
        return 0.0
    return ((data[-1] - data[-2]) / data[-2]) * 100


# Navigation state
selected_page: Signal[str] = Signal("Overview")
nav_items = ["Overview", "Analytics", "Reports", "Settings"]


def update_multiplier(value: str) -> None:
    """Update sales data based on slider input."""
    try:
        multiplier = float(value) / 100
        base = [120, 150, 180, 200, 175, 220, 250]
        sales_data.value = [int(v * multiplier) for v in base]
    except ValueError:
        pass


@component
async def Header() -> Element:
    """Dashboard header."""
    with (
        Flex(
            direction="row",
            justify="space-between",
            align="center",
            padding=16,
            cls="bg-white border-b",
        ) as header,
        Text("Flow Dashboard", cls="text-xl font-semibold"),
    ):
        pass
    with Text(f"Page: {selected_page.value}"):
        pass
    return header


@component
async def Dashboard() -> Element:
    """Main dashboard application."""
    with Flex(direction="column", height="100vh") as app:
        # Header - fixed height
        await Header()

        # Body - fills remaining space
        with Flex(direction="row", flex_grow=1):
            # Sidebar - fixed width
            await Sidebar(items=nav_items, selected=selected_page)

            # Main content - fills remaining width
            with Flex(
                direction="column",
                flex_grow=1,
                padding=24,
                gap=24,
                cls="bg-gray-100",
            ):
                # Metrics row
                with Flex(direction="row", gap=16, wrap="wrap"):
                    await MetricCard(
                        title="Total Sales",
                        value=total_sales,
                        unit="$",
                        change=sales_trend(),
                    )
                    await MetricCard(
                        title="Average Sale",
                        value=average_sales,
                        unit="$",
                    )
                    await MetricCard(
                        title="Active Users",
                        value=user_count,
                    )
                    await MetricCard(
                        title="Conversion",
                        value=conversion_rate,
                        unit="%",
                    )

                # Interactive section
                with Box(padding=16, cls="bg-white rounded-lg shadow"), VStack(gap=8):
                    with Text("Adjust Sales Multiplier", cls="font-semibold"):
                        pass
                    with Flex(direction="row", gap=16, align="center"):
                        with Input(placeholder="100", on_change=update_multiplier):
                            pass
                        with Text("% of baseline"):
                            pass

    return app


# Create and run server
app = create_app(Dashboard)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
