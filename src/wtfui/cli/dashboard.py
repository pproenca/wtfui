from wtfui import Signal, component
from wtfui.core.style import Style
from wtfui.ui import Box, Div, HStack, Text, VStack


@component
async def DevDashboard(
    status: Signal[str] | None = None,
    logs: Signal[list[str]] | None = None,
    connections: Signal[int] | None = None,
) -> None:
    if status is None:
        status = Signal("Initializing...")
    if logs is None:
        logs = Signal([])
    if connections is None:
        connections = Signal(0)

    with Div(cls="dashboard", style=Style(w="100%", h="100%")):
        with Box(cls="header border-b", style=Style(h=3)):
            Text("Fuse Dev Server", cls="text-bold text-cyan")

        with HStack(gap=2, style=Style(flex_grow=1)):
            with VStack(cls="status-panel", gap=1, style=Style(w=30)):
                Text("Status", cls="text-bold")
                Text(status.value, cls="text-green" if "Running" in status.value else "text-yellow")
                Text(f"Connections: {connections.value}")

            with VStack(cls="log-panel", gap=0, style=Style(flex_grow=1)):
                Text("Logs", cls="text-bold")
                for log in logs.value[-10:]:
                    Text(log, cls="text-dim")

        with Box(cls="footer border-t", style=Style(h=1)):
            Text("Press 'q' to quit | 'r' to reload", cls="text-dim")


@component
async def BuildProgress(
    current: Signal[int] | None = None,
    total: Signal[int] | None = None,
    message: Signal[str] | None = None,
) -> None:
    if current is None:
        current = Signal(0)
    if total is None:
        total = Signal(100)
    if message is None:
        message = Signal("Building...")

    progress_pct = (current.value / total.value * 100) if total.value > 0 else 0
    bar_width = 40
    filled = int(bar_width * progress_pct / 100)
    empty = bar_width - filled

    with VStack(gap=1, style=Style(w=bar_width + 10)):
        Text(message.value)
        with HStack():
            Text("[")
            Text("=" * filled, cls="text-green")
            Text(" " * empty)
            Text("]")
            Text(f" {progress_pct:.0f}%")
