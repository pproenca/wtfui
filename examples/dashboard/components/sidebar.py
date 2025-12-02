# examples/dashboard/components/sidebar.py
"""Sidebar navigation component."""

from __future__ import annotations

from typing import Any

from flow import Element, Signal, component
from flow.ui import Box, Button, Text, VStack


def _make_click_handler(selected: Signal[str], item: str) -> Any:
    """Create a click handler for a sidebar item."""

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
    with Box(width=200, cls="bg-gray-800 text-white") as sidebar, VStack(gap=0):
        with Box(padding=16), Text("Dashboard", cls="text-xl font-bold"):
            pass

        for item in items:
            is_active = selected.value == item
            cls = (
                f"w-full text-left px-4 py-2 {'bg-gray-700' if is_active else 'hover:bg-gray-700'}"
            )
            with Button(label=item, on_click=_make_click_handler(selected, item), cls=cls):
                pass

    return sidebar
