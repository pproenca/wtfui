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
    """Modern navigation sidebar with refined styling.

    Args:
        items: List of navigation item labels
        selected: Signal tracking currently selected item
    """
    with Box(
        width=240,
        style=Style(
            bg=Colors.Slate._900,
            color="white",
            border_right=True,
            border_color=Colors.Slate._800,
        ),
    ) as sidebar:
        with Flex(direction="column", gap=0):
            # Brand section
            with Box(
                padding=20,
                style=Style(border_bottom=True, border_color=Colors.Slate._800),
            ):
                Text("Dashboard", style=Style(font_size="lg", font_weight="bold"))

            # Navigation section
            with Box(padding=12):
                Text(
                    "NAVIGATION",
                    style=Style(font_size="sm", color=Colors.Slate._500, font_weight="bold"),
                )
                with Flex(direction="column", gap=4):
                    for item in items:
                        is_active = selected.value == item
                        button_style = Style(
                            w_full=True,
                            text_align="left",
                            px=12,
                            py=10,
                            rounded="md",
                            bg=Colors.Slate._800 if is_active else None,
                            color="white" if is_active else Colors.Slate._400,
                            font_weight="bold" if is_active else None,
                            border_left=is_active,
                            border_color=Colors.Blue._500 if is_active else None,
                        )
                        Button(
                            label=item,
                            on_click=_make_click_handler(selected, item),
                            style=button_style,
                        )

    return sidebar
