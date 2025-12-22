# WtfUI

A Pythonic UI framework for building interactive web applications entirely in Python.

WtfUI uses Python's context managers to define UI hierarchy (indentation = topology) and a reactive signal system for state management. No JavaScript required.

## Prerequisites

- **Python 3.14+** (No-GIL build required)
- **uv** package manager

## Quick Start

```bash
# Clone and setup
git clone https://github.com/pproenca/wtfui.git
cd wtfui
make setup
```

## Demo Examples

WtfUI includes four example applications demonstrating different capabilities.

### Web Examples

Run any of these in separate terminals:

```bash
# Todo App - Signal reactivity and Effect persistence
cd examples/todo && uv run wtfui dev --web
# Open http://localhost:8000

# Dashboard - Computed values and Flexbox layout
cd examples/dashboard && uv run wtfui dev --web
# Open http://localhost:8001

# Chat - @rpc decorator for server functions
cd examples/chat && uv run wtfui dev --web
# Open http://localhost:8002
```

### TUI Example

```bash
# Console - Terminal-based system monitor
cd examples/console && uv run wtfui dev
# Renders directly in terminal (press 'q' to quit)
```

## Web vs TUI Mode

WtfUI supports two rendering modes:

| Mode | Command | Output |
|------|---------|--------|
| **TUI** (default) | `wtfui dev` | Terminal-based UI |
| **Web** | `wtfui dev --web` | Browser at localhost |

## Core Concepts

### Signals (Reactive State)

```python
from wtfui import Signal

count = Signal(0)
count.value += 1  # Triggers reactive updates
```

### Context Manager UI

```python
from wtfui.ui import Flex, Box, Text

with Flex(direction="column"):
    with Box(padding=10):
        Text("Hello, WtfUI!")
```

### RPC (Server Functions)

```python
from wtfui import rpc

@rpc
def save_data(data: dict) -> bool:
    # Runs on server, client gets fetch stub
    db.save(data)
    return True
```

## Architecture

See [MANIFEST.md](MANIFEST.md) for architectural principles.

## Development

```bash
make test      # Run tests
make lint      # Run linters
make check     # All pre-commit hooks
```
