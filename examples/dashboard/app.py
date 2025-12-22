# examples/dashboard/app.py
"""Dashboard - Art Deco Geometric Luxury theme.

This example showcases:
- Flex/Box layout (CSS Flexbox)
- Computed for derived values
- Responsive sizing (flex_grow)
- Component composition

Run with: cd examples/dashboard && uv run wtfui dev --web
"""

from components import MetricCard, Sidebar

from wtfui import Computed, Element, Signal, component
from wtfui.ui import Flex, Input, Text
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
    """Art Deco luxury header with gold accents on dark background."""
    with Flex(
        direction="row",
        align="center",
        justify="space-between",
        height=64,
        padding=(0, 24),
        cls="bg-slate-950 border-b border-slate-800",
    ) as header:
        # Brand area with geometric logo
        with Flex(direction="row", align="center", gap=12):
            # Geometric Art Deco logo
            with Flex(
                direction="row",
                align="center",
                justify="center",
                width=32,
                height=32,
                cls="bg-gradient-to-br from-amber-400 to-amber-600",
            ):
                Text("F", cls="text-slate-950 font-black text-sm")
            Text("FLOW", cls="text-slate-100 font-bold tracking-widest")

        # Current page indicator with geometric accent
        with Flex(direction="row", align="center", gap=12):
            Flex(direction="row", width=4, height=16, cls="bg-amber-500")
            Text(
                _selected_page.value.upper(),
                cls="text-amber-400 text-sm font-bold tracking-widest",
            )

    return header


@component
async def Dashboard() -> Element:
    """Art Deco luxury dashboard with dark theme and gold accents."""
    with Flex(direction="column", height="100vh", cls="bg-slate-950") as app:
        # Header - fixed height
        await Header()

        # Body - fills remaining space
        with Flex(direction="row", flex_grow=1, cls="overflow-hidden"):
            # Sidebar - fixed width
            await Sidebar(items=_NAV_ITEMS, selected=_selected_page)

            # Main content - dark gradient background
            with Flex(
                direction="column",
                flex_grow=1,
                padding=32,
                gap=32,
                cls="overflow-auto bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950",
            ):
                # Page title section with Art Deco styling
                with Flex(direction="row", align="center", gap=16):
                    # Geometric accent
                    Flex(
                        direction="row",
                        width=4,
                        height=32,
                        cls="bg-gradient-to-b from-amber-400 to-amber-600",
                    )
                    with Flex(direction="column", gap=4):
                        Text(
                            _selected_page.value.upper(),
                            cls="text-2xl font-bold text-slate-100 tracking-tight",
                        )
                        Text(
                            "Monitor your key metrics and performance indicators",
                            cls="text-sm text-slate-500",
                        )

                # Metrics section
                with Flex(direction="column", gap=16):
                    with Flex(direction="row", align="center", gap=8):
                        Flex(direction="row", width=8, height=8, cls="bg-amber-500")
                        Text(
                            "KEY METRICS",
                            cls="text-xs font-bold tracking-widest text-amber-500/70",
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

                # Interactive section with Art Deco styling
                with Flex(
                    direction="column",
                    padding=24,
                    gap=20,
                    cls="bg-slate-800/30 border border-slate-700 rounded-lg",
                ):
                    # Gold accent bar
                    with Flex(direction="row", height=1, cls="mb-2"):
                        Flex(direction="row", width=96, height=1, cls="bg-amber-500")
                        Flex(direction="row", flex_grow=1, height=1, cls="bg-slate-700")

                    with Flex(direction="column", gap=4):
                        Text(
                            "ADJUST MULTIPLIER",
                            cls="text-xs font-bold tracking-widest text-amber-500",
                        )
                        Text(
                            "Modify the baseline sales data to simulate different scenarios",
                            cls="text-sm text-slate-400",
                        )

                    with Flex(direction="row", gap=16, align="center"):
                        Input(
                            bind=_multiplier_input,
                            placeholder="100",
                            on_change=update_multiplier,
                            cls=(
                                "w-28 px-4 py-2 bg-slate-900 border border-slate-600 "
                                "text-slate-100 rounded "
                                "focus:outline-none focus:border-amber-500 "
                                "transition-colors"
                            ),
                        )
                        Text("% of baseline", cls="text-sm text-slate-500")

    return app


# Create and run server
app = create_app(Dashboard)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
