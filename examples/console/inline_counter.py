#!/usr/bin/env python3
"""Inline counter example demonstrating inline TUI mode.

This example shows how to use `run_tui(inline=True)` to render
a TUI application in-place without using the alternate screen buffer.
The output remains visible after the application exits.

Usage:
    python examples/console/inline_counter.py
"""

from wtfui import Signal, component
from wtfui.tui.renderer import run_tui
from wtfui.ui import HStack, Text, VStack

# Module-level state shared between component and key handler
_count = Signal(0)


def handle_key(key: str) -> None:
    """Handle keyboard input for counter."""
    if key == "+" or key == "=":
        _count.value += 1
    elif key == "-":
        _count.value -= 1


@component
def Counter():
    """A simple counter that renders inline."""
    with VStack(height=3):
        Text("Inline Counter (q to quit, +/- to change)")
        with HStack(gap=2):
            Text(f"Count: {_count.value}")
        Text("Press + or - to change the count")


if __name__ == "__main__":
    run_tui(Counter, inline=True, on_key=handle_key)
