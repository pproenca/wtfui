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
from dataclasses import dataclass, field
from enum import Enum, auto

# Check for psutil availability
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


# ============================================================
# STEP 2: Application State
# ============================================================


class FocusArea(Enum):
    """Which UI area has keyboard focus."""

    SIDEBAR = auto()
    PROCESSES = auto()
    COMMAND = auto()


@dataclass
class ProcessInfo:
    """Information about a running process."""

    pid: int
    name: str
    cpu_percent: float
    memory_mb: float


@dataclass
class SystemStats:
    """Current system resource statistics."""

    cpu_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0


@dataclass
class AppState:
    """Application state for the system monitor.

    This dataclass holds all mutable state for the dashboard:
    - Terminal dimensions
    - Current focus area
    - Command input buffer
    - Process list scroll position
    - System statistics cache
    - Running flag for main loop
    """

    width: int
    height: int
    running: bool = True
    focus: FocusArea = FocusArea.PROCESSES
    command_input: str = ""
    scroll_offset: int = 0
    filter_text: str = ""
    sort_by: str = "cpu"  # "cpu" or "mem" or "name"
    stats: SystemStats = field(default_factory=SystemStats)
    processes: list[ProcessInfo] = field(default_factory=list)
    status_message: str = ""
    spinner_frame: int = 0

    def cycle_focus(self) -> None:
        """Cycle to next focus area (Tab key)."""
        order = [FocusArea.PROCESSES, FocusArea.COMMAND, FocusArea.SIDEBAR]
        current_idx = order.index(self.focus)
        self.focus = order[(current_idx + 1) % len(order)]

    def type_char(self, char: str) -> None:
        """Add character to command input."""
        self.command_input += char

    def backspace(self) -> None:
        """Remove last character from command input."""
        self.command_input = self.command_input[:-1]

    def clear_command(self) -> None:
        """Clear command input buffer."""
        self.command_input = ""

    def scroll_up(self) -> None:
        """Scroll process list up."""
        if self.scroll_offset > 0:
            self.scroll_offset -= 1

    def scroll_down(self, max_items: int) -> None:
        """Scroll process list down."""
        visible_height = self.height - 4  # Account for header/footer
        max_offset = max(0, max_items - visible_height)
        if self.scroll_offset < max_offset:
            self.scroll_offset += 1


# ============================================================
# STEP 3: System Data Collection
# ============================================================


def collect_stats() -> SystemStats:
    """Collect current system statistics using psutil.

    Returns:
        SystemStats with CPU, memory, and disk usage.
    """
    if not HAS_PSUTIL or psutil is None:
        return SystemStats()

    # CPU (non-blocking, uses cached value from previous call)
    cpu = psutil.cpu_percent(interval=None)

    # Memory
    mem = psutil.virtual_memory()
    mem_used_gb = mem.used / (1024**3)
    mem_total_gb = mem.total / (1024**3)

    # Disk (root partition)
    try:
        disk = psutil.disk_usage("/")
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
    except Exception:
        disk_used_gb = 0.0
        disk_total_gb = 0.0

    return SystemStats(
        cpu_percent=cpu,
        memory_used_gb=mem_used_gb,
        memory_total_gb=mem_total_gb,
        disk_used_gb=disk_used_gb,
        disk_total_gb=disk_total_gb,
    )


def collect_processes(
    limit: int = 50,
    sort_by: str = "cpu",
    filter_text: str = "",
) -> list[ProcessInfo]:
    """Collect running processes using psutil.

    Args:
        limit: Maximum number of processes to return.
        sort_by: Sort key - "cpu", "mem", or "name".
        filter_text: Filter processes by name (case-insensitive).

    Returns:
        List of ProcessInfo sorted by the specified key.
    """
    if not HAS_PSUTIL or psutil is None:
        return []

    procs: list[ProcessInfo] = []

    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = proc.info
            name = info["name"] or "unknown"

            # Apply filter
            if filter_text and filter_text.lower() not in name.lower():
                continue

            mem_mb = (info["memory_info"].rss / (1024**2)) if info["memory_info"] else 0

            procs.append(
                ProcessInfo(
                    pid=info["pid"],
                    name=name[:20],  # Truncate long names
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_mb=mem_mb,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort
    if sort_by == "cpu":
        procs.sort(key=lambda p: p.cpu_percent, reverse=True)
    elif sort_by == "mem":
        procs.sort(key=lambda p: p.memory_mb, reverse=True)
    elif sort_by == "name":
        procs.sort(key=lambda p: p.name.lower())

    return procs[:limit]


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
