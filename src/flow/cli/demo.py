"""Console Demo - Interactive System Monitor Dashboard.

This module implements a tutorial-style TUI application that demonstrates
the ConsoleRenderer with Yoga layout integration.

Run with: uv run flow demo console

# ============================================================
# STEP 1: Imports and Basic Setup
# ============================================================
"""

from __future__ import annotations

import sys

# Check for psutil availability
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


def run_demo() -> None:
    """Main entry point for the console demo.

    This function is called by the CLI when running:
        uv run flow demo console
    """
    if not HAS_PSUTIL:
        print("Error: psutil is required for the demo.")
        print("Install with: uv sync --extra demo")
        sys.exit(1)

    print("System Monitor Demo")
    print("(Full implementation in subsequent tasks)")
    print("Press Ctrl+C to exit")

    try:
        # Placeholder - will be replaced with actual async loop
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    run_demo()
