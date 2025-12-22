# examples/dashboard/components/sidebar.py
"""Sidebar navigation component."""

from collections.abc import Callable  # noqa: TC003 - needed at runtime for type annotation

from wtfui import Element, Signal, component
from wtfui.core.style import Colors, Style
from wtfui.ui import Box, Button, Flex, Text


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
    """Navigation sidebar with selectable items.

    Args:
        items: List of navigation item labels
        selected: Signal tracking currently selected item
    """
    with Box(
        width=200,
        style=Style(bg=Colors.Slate._800, color="white"),
    ) as sidebar:
        with Flex(direction="column", gap=0):
            with Box(padding=16):
                Text("Dashboard", style=Style(font_size="xl", font_weight="bold"))

            for item in items:
                is_active = selected.value == item
                # Note: hover states not supported in Style, using conditional bg
                button_style = Style(
                    w_full=True,
                    text_align="left",
                    px=4,
                    py=2,
                    bg=Colors.Slate._700 if is_active else None,
                )
                Button(
                    label=item,
                    on_click=_make_click_handler(selected, item),
                    style=button_style,
                )

    return sidebar
