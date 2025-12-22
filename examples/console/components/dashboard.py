"""Dashboard Component for Console Demo.

The root component that composes the entire System Monitor UI.
Manages state, background polling via async Effect, and layout.

Usage:
    from wtfui.tui.renderer import run_tui
    from components import Dashboard

    run_tui(Dashboard)
"""

import asyncio
import types  # noqa: TC003 - needed at runtime for type annotation
from typing import Any

from state import SystemState

from wtfui import Effect, component
from wtfui.core.style import Colors, Style
from wtfui.ui import HStack, Input, Text, VStack

from .process_list import ProcessList
from .progress_bar import ProgressBar

# Only import psutil if available
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil: types.ModuleType | None = None  # type: ignore[no-redef]
    HAS_PSUTIL = False


def _get_cpu_percent() -> float:
    """Blocking call to get CPU percentage (runs in thread)."""
    if psutil is None:
        return 0.0
    return float(psutil.cpu_percent())


def _get_memory_percent() -> float:
    """Blocking call to get memory percentage (runs in thread)."""
    if psutil is None:
        return 0.0
    return float(psutil.virtual_memory().percent)


def _get_processes() -> list[dict[str, Any]]:
    """Blocking call to get process list (runs in thread)."""
    if psutil is None:
        return []
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p.get("cpu_percent", 0) or 0, reverse=True)
    return procs


async def _poll_stats(state: SystemState) -> None:
    """Async background polling function for system stats.

    Uses asyncio.to_thread for blocking psutil calls to avoid
    freezing the AsyncIO event loop (Manifesto Tenet IV: Native Leverage).

    Updates Signal values which triggers automatic re-renders.

    Handles cancellation gracefully for clean shutdown.
    """
    if not HAS_PSUTIL:
        return

    try:
        while True:
            # Run blocking psutil calls in thread pool
            cpu, mem, procs = await asyncio.gather(
                asyncio.to_thread(_get_cpu_percent),
                asyncio.to_thread(_get_memory_percent),
                asyncio.to_thread(_get_processes),
            )

            # Update signals (triggers re-renders)
            state.cpu_percent.value = cpu
            state.memory_percent.value = mem
            state.processes.value = procs

            # Non-blocking sleep
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Clean shutdown - re-raise to properly cancel
        raise


@component
def Dashboard() -> None:
    """Root component for the System Monitor Dashboard.

    Creates SystemState, starts async background polling via Effect,
    and renders the complete dashboard layout.

    Task management is encapsulated within the component scope to avoid
    global mutable state.
    """
    state = SystemState()

    # Component-scoped task reference (NOT a Signal to avoid reactive loop)
    # Using a mutable container (list) allows nonlocal-free closure mutation
    polling_task: list[asyncio.Task[None] | None] = [None]

    def start_polling() -> None:
        """Start background polling with component-scoped task tracking.

        Note: This function reads/writes polling_task[0] which is NOT a Signal,
        so the Effect runs exactly once (no reactive dependencies to trigger re-runs).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        task = polling_task[0]
        if task is not None and not task.done():
            task.cancel()

        polling_task[0] = loop.create_task(_poll_stats(state))

    # Effect starts async polling with proper task tracking
    Effect(start_polling)

    # Layout: Indentation is Topology (Flow Manifesto Tenet I)
    # Layout props go directly on elements; Style handles visual styling only
    with VStack(height="100%", style=Style(bg=Colors.Slate._900)):
        # Header Section
        with HStack(
            height=3,
            align_items="center",
            justify_content="center",
            style=Style(bg=Colors.Blue._600),
        ):
            Text("System Monitor", style=Style(font_weight="bold", color="white"))

        # Main Content
        with HStack(flex_grow=1):
            # Sidebar (Stats)
            with VStack(width=30, padding=2, style=Style(border_right=True)):
                Text("Resources", style=Style(color="gray", mb=1))

                Text("CPU Usage")
                ProgressBar(state.cpu_percent, color="green")

                Text("Memory Usage", style=Style(mt=1))
                ProgressBar(state.memory_percent, color="cyan")

            # Main Area (Process List)
            with VStack(flex_grow=1, padding=2):
                Text("Processes", style=Style(color="gray", mb=1))
                ProcessList(state)

        # Footer (Command Bar)
        with HStack(
            height=3,
            align_items="center",
            padding=1,
            style=Style(border_top=True),
        ):
            Text("> ", style=Style(color="green"))
            Input(bind=state.filter_text, placeholder="Filter processes...")
