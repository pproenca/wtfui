# examples/dashboard/components/sidebar.py
"""Sidebar navigation component - Art Deco Geometric Luxury theme."""

from collections.abc import Callable  # noqa: TC003 - needed at runtime for type annotation

from wtfui import Element, Signal, component
from wtfui.ui import Button, Flex, Text


def _make_click_handler(selected: Signal[str], item: str) -> Callable[[], None]:
    """Create a click handler that sets the selected signal to the given item.

    This factory pattern avoids closure capture issues in loops where
    inline lambdas would all reference the same loop variable.
    """

    def handler() -> None:
        selected.value = item

    return handler


@component
async def Sidebar(
    items: list[str],
    selected: Signal[str],
) -> Element:
    """Art Deco luxury sidebar with gold accents on deep navy.

    Args:
        items: List of navigation item labels
        selected: Signal tracking currently selected item
    """
    with Flex(
        direction="column",
        width=200,
        flex_shrink=0,
        cls="bg-slate-950 border-r border-slate-800",
    ) as sidebar:
        # Decorative geometric line at top
        with Flex(direction="row", height=1):
            Flex(direction="row", width="30%", height=1, cls="bg-amber-500")
            Flex(direction="row", flex_grow=1, height=1, cls="bg-slate-800")

        # Navigation section
        with Flex(direction="column", padding=16, gap=12, flex_grow=1):
            Text("NAVIGATION", cls="text-amber-500/70 text-xs font-bold tracking-widest")

            with Flex(direction="column", gap=2):
                for item in items:
                    is_active = selected.value == item

                    # Art Deco styled navigation buttons
                    if is_active:
                        btn_cls = (
                            "w-full text-left px-4 py-3 "
                            "bg-slate-900/50 text-amber-400 font-semibold "
                            "border-l-2 border-amber-500 "
                            "transition-all duration-200"
                        )
                    else:
                        btn_cls = (
                            "w-full text-left px-4 py-3 "
                            "text-slate-400 "
                            "hover:bg-slate-900/30 hover:text-amber-300 "
                            "border-l-2 border-transparent "
                            "transition-all duration-200"
                        )

                    Button(
                        label=item,
                        on_click=_make_click_handler(selected, item),
                        cls=btn_cls,
                    )

        # Bottom decorative element
        with Flex(direction="row", padding=16, cls="border-t border-slate-800"):
            with Flex(direction="row", align="center", gap=8):
                Flex(direction="row", width=6, height=6, cls="bg-amber-500")
                Text("Premium", cls="text-slate-600 text-xs tracking-wide")

    return sidebar
