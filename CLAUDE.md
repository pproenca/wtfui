# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flow is a Pythonic UI framework using context managers and signals. It requires **Python 3.14+** for No-GIL (PEP 703) and deferred annotations (PEP 649).

Core principles (from MANIFEST.md):
- **Indentation is Topology**: Use `with Div():` context managers for DOM hierarchy, not function nesting
- **Atomic Reactivity**: `Signal` → `Effect` → `Computed` for fine-grained updates (no Virtual DOM diffing)
- **Universal Isomorphism**: Elements describe themselves to `Renderer`, never know how to render (Bridge Pattern)
- **Zero-Build Dev**: `python app.py` starts full-stack dev; import hooks handle transpilation

## Commands

```bash
# Setup
uv sync --dev                    # Install dependencies
uv run pre-commit install        # Install git hooks

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_signal.py  # Single test file
uv run pytest -k "test_name"     # Run specific test
uv run pytest --cov=src/flow     # With coverage report

# Linting/Formatting
uv run ruff check --fix src/ tests/  # Lint with auto-fix
uv run ruff format src/ tests/       # Format code

# Type Checking
uv run mypy src/ tests/

# Pre-commit (runs all checks: ruff, mypy, bandit, commitizen)
uv run pre-commit run --all-files

# CLI
uv run flow dev     # Start dev server
uv run flow build   # Production build
uv run flow new     # Create new project
```

## Architecture

### Reactivity System (`flow.signal`, `flow.effect`, `flow.computed`)
Thread-safe reactive primitives using `threading.Lock` for No-GIL safety:
- `Signal[T]`: Observable value with subscriber notifications
- `Effect`: Side effects that auto-track signal dependencies
- `Computed`: Derived values with lazy evaluation and caching

### Element System (`flow.element`, `flow.ui.elements`)
- `Element`: Base class using context managers (`__enter__`/`__exit__`) for DOM hierarchy
- Uses `contextvars` via `flow.context` to track parent-child relationships
- Elements convert to `RenderNode` (abstract representation)

### Renderer Protocol (`flow.renderer.protocol`)
- `RenderNode`: Abstract node representation decoupled from rendering
- `Renderer` ABC with implementations: `HTMLRenderer` (SSR), `DOMRenderer` (Wasm)

### Component Decorator (`flow.component`)
- `@component` decorator for async UI functions
- Uses PEP 649 `annotationlib` for lazy type hint resolution
- Supports dependency injection via `flow.injection`

### RPC System (`flow.rpc`)
- `@rpc` decorator registers server functions
- AST transformation strips server code from client bundles (security firewall)
- Client receives fetch stubs instead of actual implementation

### Server (`flow.server`)
- FastAPI-based with WebSocket support
- Session management for stateful connections

### Layout Engine (`flow.layout`)
Yoga-compatible Flexbox implementation for computing element positions:
- `LayoutNode`: Tree node with `FlexStyle`, computed `LayoutResult`, optional `measure_func` for leaf nodes
- `FlexStyle`: Immutable (frozen) dataclass with all CSS Flexbox properties
- `compute_layout(node, available_size)`: Main entry point for layout computation
- **Layout Boundary**: Nodes with explicit width AND height can be computed in parallel
- Supports: flex-direction, flex-wrap, justify-content, align-items, align-content, gap, aspect-ratio, min/max constraints, intrinsic sizing (min-content, max-content, fit-content), absolute positioning

## Key Patterns

**UI Definition (context managers, not nesting):**
```python
with Div(class_="container"):
    with VStack():
        Text("Hello")
```

**Reactivity:**
```python
count = Signal(0)
count.value += 1  # Notifies subscribers automatically
```

**Components:**
```python
@component
async def Counter():
    count = Signal(0)
    with Button(on_click=lambda: setattr(count, 'value', count.value + 1)):
        Text(f"Count: {count.value}")
```

**Layout computation:**
```python
from flow.layout.node import LayoutNode
from flow.layout.compute import compute_layout
from flow.layout.types import Size

# Convert element tree to layout tree
layout_root = element.to_layout_node()
compute_layout(layout_root, Size(800, 600))

# Render with computed positions
render_node = element.to_render_node_with_layout(layout_root)
```

## Commit Convention

Uses Conventional Commits (enforced by commitizen pre-commit hook):
- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation
- `refactor:` code changes without feature/fix
- `test:` test additions/changes
- `chore:` maintenance tasks
