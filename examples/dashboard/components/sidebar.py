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
        cls="w-60 min-h-screen bg-slate-950 border-r border-slate-800",
    ) as sidebar:
        # Brand section with geometric accent
        with Flex(direction="column", cls="p-5 border-b border-slate-800"):
            with Flex(direction="row", cls="items-center gap-3"):
                # Geometric logo mark
                with Flex(
                    direction="row",
                    cls=(
                        "w-8 h-8 bg-gradient-to-br from-amber-400 to-amber-600 "
                        "items-center justify-center"
                    ),
                ):
                    with Flex(direction="row"):
                        Text("D", cls="text-slate-950 font-black text-sm")
                with Flex(direction="row"):
                    Text("DASHBOARD", cls="text-slate-100 font-bold tracking-widest text-sm")

        # Decorative geometric line
        with Flex(direction="row", cls="h-px w-full"):
            Flex(direction="row", cls="h-full w-1/4 bg-amber-500")
            Flex(direction="row", cls="h-full w-3/4 bg-slate-800")

        # Navigation section
        with Flex(direction="column", cls="p-4 space-y-4"):
            with Flex(direction="row"):
                Text("NAVIGATION", cls="text-amber-500/70 text-xs font-bold tracking-widest")

            with Flex(direction="column", cls="space-y-1"):
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

                    with Flex(direction="row"):
                        Button(
                            label=item,
                            on_click=_make_click_handler(selected, item),
                            cls=btn_cls,
                        )

        # Bottom decorative element
        with Flex(direction="column", cls="mt-auto p-4 border-t border-slate-800"):
            with Flex(direction="row", cls="items-center gap-2"):
                Flex(direction="row", cls="w-2 h-2 bg-amber-500")
                with Flex(direction="row"):
                    Text("Premium Analytics", cls="text-slate-600 text-xs tracking-wide")

    return sidebar
