# Console System Monitor

A terminal-based system monitor demonstrating TUI rendering and async polling.

## Run

```bash
uv run wtfui dev
# Renders directly in terminal
# Press 'q' to quit
```

**Note**: This is a TUI (Terminal User Interface) app - no `--web` flag needed.

## Prerequisites

Requires `psutil` for system monitoring:

```bash
uv sync  # Installs dependencies from pyproject.toml
```

## Patterns Demonstrated

| Pattern | Usage |
|---------|-------|
| **TUI rendering** | `run_tui(Dashboard)` for terminal UI |
| **Async polling** | `asyncio.to_thread()` for blocking psutil calls |
| **Signal reactivity** | Real-time CPU/memory updates |
| **Process monitoring** | Filtered process list with Computed |
| **ProgressBar** | Visual meters for CPU/memory |

## Key Files

- `app.py` - Entry point with `run_demo()`
- `components/dashboard.py` - Main dashboard with async polling
- `components/progress_bar.py` - ProgressBar component
- `components/process_list.py` - Scrollable process list
- `state.py` - SystemState dataclass managing signals

## Code Highlights

```python
# TUI entry point
from wtfui.tui.renderer import run_tui
run_tui(Dashboard)

# Non-blocking psutil calls
cpu = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
state.cpu_percent.value = cpu

# Signal-reactive ProgressBar
ProgressBar(
    value=state.cpu_percent,  # Updates automatically
    max_value=100,
    label="CPU",
)
```

## Web vs TUI

| Feature | TUI (this example) | Web examples |
|---------|-------------------|--------------|
| Command | `wtfui dev` | `wtfui dev --web` |
| Output | Terminal | Browser |
| Renderer | TUIRenderer | HTMLRenderer |
