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
_multiplier_input: Signal[str] = Signal("100")


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
    previous = data[-2]
    if previous == 0:
        return 0.0
    return ((data[-1] - previous) / previous) * 100


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
    """Premium header with refined typography and subtle elevation."""
    with Flex(
        direction="row",
        justify="space-between",
        align="center",
        padding=24,
        height=72,
        style=Style(
            bg="white",
            border_bottom=True,
            border_color=Colors.Slate._100,
            shadow="sm",
        ),
    ) as header:
        # Brand area with icon
        with Flex(direction="row", align="center", gap=12):
            with Box(
                width=32,
                height=32,
                style=Style(bg=Colors.Blue._600, rounded="md"),
            ):
                Text("W", style=Style(color="white", font_weight="bold"))
            Text(
                "Flow",
                style=Style(font_size="xl", font_weight="bold", color=Colors.Slate._900),
            )
        # Current page indicator
        Text(
            _selected_page.value,
            style=Style(font_size="sm", color=Colors.Slate._600, font_weight="bold"),
        )
    return header


@component
async def Dashboard() -> Element:
    """Premium dashboard with modern layout and refined styling."""
    with Flex(direction="column", height="100vh") as app:
        # Header - fixed height
        await Header()

        # Body - fills remaining space
        with Flex(direction="row", flex_grow=1):
            # Sidebar - fixed width
            await Sidebar(items=_NAV_ITEMS, selected=_selected_page)

            # Main content - pure white background with generous spacing
            with Flex(
                direction="column",
                flex_grow=1,
                padding=32,
                gap=32,
                style=Style(bg="white"),
            ):
                # Page title section
                with Flex(direction="column", gap=4):
                    Text(
                        _selected_page.value,
                        style=Style(
                            font_size="2xl",
                            font_weight="bold",
                            color=Colors.Slate._900,
                        ),
                    )
                    Text(
                        "Monitor your key metrics and performance indicators",
                        style=Style(font_size="sm", color=Colors.Slate._500),
                    )

                # Metrics section
                with Flex(direction="column", gap=12):
                    Text(
                        "Key Metrics",
                        style=Style(
                            font_size="sm",
                            font_weight="bold",
                            color=Colors.Slate._500,
                        ),
                    )
                    with Flex(direction="row", gap=20, wrap="wrap"):
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

                # Interactive section with refined styling
                with Box(
                    padding=24,
                    style=Style(
                        bg=Colors.Slate._50,
                        rounded="lg",
                        border=True,
                        border_color=Colors.Slate._200,
                    ),
                ):
                    with Flex(direction="column", gap=16):
                        with Flex(direction="column", gap=4):
                            Text(
                                "Adjust Sales Multiplier",
                                style=Style(
                                    font_size="lg",
                                    font_weight="bold",
                                    color=Colors.Slate._900,
                                ),
                            )
                            Text(
                                "Modify the baseline sales data to simulate different scenarios",
                                style=Style(font_size="sm", color=Colors.Slate._500),
                            )
                        with Flex(direction="row", gap=16, align="center"):
                            Input(
                                bind=_multiplier_input,
                                placeholder="100",
                                on_change=update_multiplier,
                                width=120,
                                style=Style(
                                    border=True,
                                    border_color=Colors.Slate._300,
                                    rounded="md",
                                    px=12,
                                    py=8,
                                ),
                            )
                            Text(
                                "% of baseline",
                                style=Style(color=Colors.Slate._500, font_size="sm"),
                            )

    return app


# Create and run server
app = create_app(Dashboard)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
