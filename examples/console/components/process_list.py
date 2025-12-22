"""ProcessList Component for Console Demo.

Displays a scrollable, filterable list of system processes.
Uses Computed for automatic filtering when filter_text changes.

Usage:
    ProcessList(state=system_state)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from state import SystemState

from wtfui import Computed, component
from wtfui.core.style import Colors, Style
from wtfui.ui import For, HStack, Text, VStack


@component
def ProcessList(state: SystemState) -> None:
    """Render a scrollable process list with filtering.

    Args:
        state: SystemState containing processes and filter_text Signals.
    """
    # Computed automatically re-evaluates when dependencies change
    filtered_procs = Computed(
        lambda: [
            p for p in state.processes.value if state.filter_text.value.lower() in p["name"].lower()
        ]
    )

    # Layout props go directly on elements; Style handles visual styling only
    with VStack(flex_grow=1, overflow="hidden"):
        # Header row - explicit height=3 for padding + content
        with HStack(height=3, padding=1, style=Style(bg=Colors.Slate._800)):
            Text("PID", width=6, style=Style(color="white"))
            Text("Name", flex_grow=1, style=Style(color="white"))
            Text("CPU%", width=8, style=Style(color="white"))

        # Process rows (limited to 20 for demo)
        limited_procs = Computed(lambda: filtered_procs()[:20])

        def render_process_row(proc: dict, index: int) -> None:
            """Render a single process row."""
            is_selected = index == state.selected_index.value
            bg = Colors.Blue._600 if is_selected else None

            with HStack(height=1, style=Style(bg=bg) if bg else None):
                Text(str(proc["pid"]), width=6)
                Text(proc["name"], flex_grow=1)
                Text(f"{proc['cpu_percent'] or 0:.1f}", width=8)

        For(
            each=limited_procs,
            render=render_process_row,
            key=lambda p: p["pid"],
        )
