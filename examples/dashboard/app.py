# examples/dashboard/app.py
"""Dashboard - Demonstrates Flexbox layout and Computed values.

This example showcases:
- Flex/Box layout (CSS Flexbox)
- Computed for derived values
- Responsive sizing (flex_grow)
- Component composition

Run with: cd examples/dashboard && uv run wtfui dev --web
"""

from components import MetricCard, Sidebar

from wtfui import Computed, Element, Signal, component
from wtfui.core.style import Colors, Style
from wtfui.ui import Box, Flex, Input, Text
from wtfui.web.server import create_app

# Sample data (module-level, prefixed with underscore per naming standard)
_sales_data: Signal[list[int]] = Signal([120, 150, 180, 200, 175, 220, 250])
_user_count: Signal[int] = Signal(1234)
_conversion_rate: Signal[float] = Signal(3.2)


# Computed values - automatically update when dependencies change
@Computed
def _total_sales() -> int:
    return sum(_sales_data.value)


@Computed
def _average_sales() -> float:
    data = _sales_data.value
    return sum(data) / len(data) if data else 0.0


@Computed
def _sales_trend() -> float:
    """Calculate week-over-week change."""
    data = _sales_data.value
    if len(data) < 2:
        return 0.0
    return ((data[-1] - data[-2]) / data[-2]) * 100


# Navigation state
_selected_page: Signal[str] = Signal("Overview")
_NAV_ITEMS = ["Overview", "Analytics", "Reports", "Settings"]


def update_multiplier(value: str) -> None:
    """Update sales data based on slider input."""
    try:
        multiplier = float(value) / 100
        base = [120, 150, 180, 200, 175, 220, 250]
        _sales_data.value = [int(v * multiplier) for v in base]
    except ValueError:
        pass


@component
async def Header() -> Element:
    """Dashboard header with explicit flex styling."""
    with Flex(
        direction="row",
        justify="space-between",
        align="center",
        padding=16,
        height=64,
        style=Style(bg="white", border_bottom=True, border_color=Colors.Slate._200),
    ) as header:
        Text(
            "Flow Dashboard",
            style=Style(font_size="xl", font_weight="bold", color=Colors.Slate._800),
        )
        Text(f"Page: {_selected_page.value}", style=Style(color=Colors.Slate._500))
    return header


@component
async def Dashboard() -> Element:
    """Main dashboard with modern Flex layout."""
    with Flex(direction="column", height="100vh") as app:
        # Header - fixed height
        await Header()

        # Body - fills remaining space
        with Flex(direction="row", flex_grow=1):
            # Sidebar - fixed width
            await Sidebar(items=_NAV_ITEMS, selected=_selected_page)

            # Main content - fills remaining width
            with Flex(
                direction="column",
                flex_grow=1,
                padding=24,
                gap=24,
                style=Style(bg=Colors.Slate._50),
            ):
                # Metrics row - responsive wrap
                with Flex(direction="row", gap=16, wrap="wrap"):
                    await MetricCard(
                        title="Total Sales",
                        value=_total_sales,
                        unit="$",
                        change=_sales_trend(),
                    )
                    await MetricCard(
                        title="Average Sale",
                        value=_average_sales,
                        unit="$",
                    )
                    await MetricCard(
                        title="Active Users",
                        value=_user_count,
                    )
                    await MetricCard(
                        title="Conversion",
                        value=_conversion_rate,
                        unit="%",
                    )

                # Interactive section with Box container
                with Box(
                    padding=16,
                    style=Style(bg="white", rounded="lg", shadow="sm"),
                ):
                    with Flex(direction="column", gap=8):
                        Text(
                            "Adjust Sales Multiplier",
                            style=Style(font_weight="bold", color=Colors.Slate._700),
                        )
                        with Flex(direction="row", gap=16, align="center"):
                            Input(
                                placeholder="100",
                                on_change=update_multiplier,
                                width=100,
                            )
                            Text("% of baseline", style=Style(color=Colors.Slate._500))

    return app


# Create and run server
app = create_app(Dashboard)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
