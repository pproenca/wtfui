"""Reactive State for Console System Monitor Demo.

This module defines SystemState using Flow Signals for automatic
UI updates when state changes.

Usage:
    state = SystemState()
    state.cpu_percent.value = 75.0  # Triggers re-render of subscribers
"""

from typing import Any

from wtfui import Signal


class SystemState:
    """Reactive state container for the System Monitor.

    All properties are Signals, enabling automatic re-renders when values change.
    Components that read these signals automatically subscribe to changes.

    Attributes:
        cpu_percent: Current CPU usage percentage (0-100).
        memory_percent: Current memory usage percentage (0-100).
        processes: List of process info dicts with pid, name, cpu_percent keys.
        filter_text: Text to filter process list (bound to Input).
        selected_index: Currently selected process index in list.
    """

    def __init__(self) -> None:
        """Initialize all state Signals with default values."""
        # System metrics
        self.cpu_percent: Signal[float] = Signal(0.0)
        self.memory_percent: Signal[float] = Signal(0.0)
        self.processes: Signal[list[dict[str, Any]]] = Signal([])

        # UI state
        self.filter_text: Signal[str] = Signal("")
        self.selected_index: Signal[int] = Signal(0)
