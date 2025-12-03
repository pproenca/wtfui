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
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING

from flow.layout.node import LayoutNode
from flow.layout.style import FlexDirection, FlexStyle, JustifyContent
from flow.layout.types import Dimension

if TYPE_CHECKING:
    from flow.renderer.console import ConsoleRenderer

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


# ============================================================
# STEP 4: Layout Tree Builder
# ============================================================


def build_layout_tree(state: AppState) -> LayoutNode:
    """Build the Yoga layout tree for the dashboard.

    This demonstrates:
    - Row and column layouts
    - Fixed and flexible sizing
    - Nested containers
    - Gap and padding
    - Alignment properties

    Args:
        state: Current application state (for dimensions).

    Returns:
        Root LayoutNode ready for compute_layout().
    """
    # ============================================================
    # ROOT: Column layout filling terminal
    # ============================================================
    root = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.COLUMN,
            width=Dimension.points(state.width),
            height=Dimension.points(state.height),
        ),
    )

    # ============================================================
    # HEADER: Row with space-between for title and clock
    # Demonstrates: justify_content=SPACE_BETWEEN
    # ============================================================
    header = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.ROW,
            justify_content=JustifyContent.SPACE_BETWEEN,
            height=Dimension.points(1),
        ),
    )
    root.add_child(header)

    # ============================================================
    # MAIN: Row with sidebar and content
    # Demonstrates: flex_grow, fixed width, gap
    # ============================================================
    main = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.ROW,
            flex_grow=1,
            gap=1,
        ),
    )
    root.add_child(main)

    # Sidebar: Fixed width column
    sidebar = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.COLUMN,
            width=Dimension.points(18),
            gap=1,
        ),
    )
    main.add_child(sidebar)

    # Content: Flexible width for process list
    content = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.COLUMN,
            flex_grow=1,
        ),
    )
    main.add_child(content)

    # ============================================================
    # FOOTER: Command input bar
    # Demonstrates: fixed height row
    # ============================================================
    footer = LayoutNode(
        style=FlexStyle(
            flex_direction=FlexDirection.ROW,
            height=Dimension.points(1),
        ),
    )
    root.add_child(footer)

    return root


# ============================================================
# STEP 5: Rendering
# ============================================================


def render_layout(
    renderer: ConsoleRenderer,
    root: LayoutNode,
    state: AppState,
) -> None:
    """Render a computed layout tree to the console renderer.

    Walks the layout tree and writes content to the renderer buffer
    at the computed positions.

    Args:
        renderer: ConsoleRenderer with back buffer.
        root: Root LayoutNode with computed layout positions.
        state: Application state with data to render.
    """
    renderer.clear()

    # Root has 3 children: header, main, footer
    # Main has 2 children: sidebar, content
    header = root.children[0]
    main = root.children[1]
    footer = root.children[2]
    sidebar = main.children[0]
    content = main.children[1]

    # Render header
    _render_header(renderer, header, state)

    # Render sidebar with stats
    _render_sidebar(renderer, sidebar, main, state)

    # Render content with process list
    _render_content(renderer, content, main, state)

    # Render footer with command input
    _render_footer(renderer, footer, state)


def _render_header(
    renderer: ConsoleRenderer,
    header: LayoutNode,
    state: AppState,
) -> None:
    """Render the header with title and clock."""
    x = int(header.layout.left)
    y = int(header.layout.top)
    width = int(header.layout.width)

    title = "System Monitor"
    clock = datetime.now().strftime("%H:%M:%S")

    # Title on left (bold, blue)
    renderer.render_text_at(x, y, title, cls="text-blue-500 bold")

    # Clock on right (dim)
    clock_x = x + width - len(clock) - 1
    renderer.render_text_at(clock_x, y, clock, cls="text-slate-400")


def _render_sidebar(
    renderer: ConsoleRenderer,
    sidebar: LayoutNode,
    main: LayoutNode,
    state: AppState,
) -> None:
    """Render the stats sidebar."""
    # Sidebar position relative to main
    x = int(main.layout.left + sidebar.layout.left)
    y = int(main.layout.top + sidebar.layout.top)

    stats = state.stats

    # Progress bar helper
    def bar(used: float, total: float, bar_width: int = 10) -> str:
        if total == 0:
            return "░" * bar_width
        ratio = min(used / total, 1.0)
        filled = int(ratio * bar_width)
        return "█" * filled + "░" * (bar_width - filled)

    lines = [
        (f"CPU  {stats.cpu_percent:5.1f}%", "text-green-400 bold"),
        (f"[{bar(stats.cpu_percent, 100)}]", "text-green-500"),
        ("", ""),
        (f"MEM  {stats.memory_used_gb:.1f}/{stats.memory_total_gb:.1f}G", "text-cyan-400 bold"),
        (f"[{bar(stats.memory_used_gb, stats.memory_total_gb)}]", "text-cyan-500"),
        ("", ""),
        (f"DISK {stats.disk_used_gb:.0f}/{stats.disk_total_gb:.0f}G", "text-yellow-400 bold"),
        (f"[{bar(stats.disk_used_gb, stats.disk_total_gb)}]", "text-yellow-500"),
    ]

    for i, (text, cls) in enumerate(lines):
        if text:
            renderer.render_text_at(x, y + i, text, cls=cls)


def _render_content(
    renderer: ConsoleRenderer,
    content: LayoutNode,
    main: LayoutNode,
    state: AppState,
) -> None:
    """Render the process list."""
    x = int(main.layout.left + content.layout.left)
    y = int(main.layout.top + content.layout.top)
    height = int(content.layout.height)

    # Header row
    header_text = f"{'PID':<8}{'NAME':<20}{'CPU%':<8}{'MEM':<10}"
    renderer.render_text_at(x, y, header_text, cls="text-white bold")

    # Process rows
    visible_count = height - 1  # Minus header
    start = state.scroll_offset
    end = start + visible_count
    visible_procs = state.processes[start:end]

    for i, proc in enumerate(visible_procs):
        mem_str = (
            f"{proc.memory_mb:.0f}MB" if proc.memory_mb < 1024 else f"{proc.memory_mb / 1024:.1f}GB"
        )
        line = f"{proc.pid:<8}{proc.name:<20}{proc.cpu_percent:<8.1f}{mem_str:<10}"
        renderer.render_text_at(x, y + 1 + i, line)


def _render_footer(
    renderer: ConsoleRenderer,
    footer: LayoutNode,
    state: AppState,
) -> None:
    """Render the command input bar."""
    x = int(footer.layout.left)
    y = int(footer.layout.top)

    cursor = "_" if state.focus == FocusArea.COMMAND else ""
    prompt = f"> {state.command_input}{cursor}"

    renderer.render_text_at(x, y, prompt, cls="text-green-300")


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
