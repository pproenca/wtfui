"""Console Demo - Interactive System Monitor.

This module demonstrates Flow Framework patterns:
- Components (via @component decorator)
- Signals (Reactive State)
- Context Managers (Topology)
- Isomorphic Rendering (No direct renderer calls)

Run with: cd examples/console && uv run wtfui dev

Flow Manifesto Tenets demonstrated:
- Tenet I (Topology): Layout via with Div(): context managers
- Tenet II (Isomorphism): Components return abstract trees
- Tenet IV (Native Leverage): asyncio.to_thread for blocking I/O
- Tenet V (Atomic Reactivity): Signal → Effect → Computed
"""

import sys

from components import Dashboard

from wtfui.tui.renderer import run_tui


def run_demo() -> None:
    """Main entry point for the console demo.

    Uses Flow's declarative patterns:
    - run_tui() for automatic event loop management
    - Dashboard component for declarative UI
    - Signal/Effect for reactive state updates
    - asyncio.to_thread for non-blocking psutil calls
    """
    try:
        import psutil  # noqa: F401
    except ImportError:
        print("Error: psutil is required for the demo.")
        print("Install with: uv sync --extra demo")
        sys.exit(1)

    # The Runtime handles the Event Loop, Renderer, and Signal Graph
    run_tui(Dashboard)


if __name__ == "__main__":
    run_demo()
