# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
make setup              # Install deps + pre-commit hooks (uv sync --extra dev --extra demo)
make test               # Unit + integration tests (excludes E2E)
make test-fast          # Excludes gatekeepers too (fastest iteration)
make test-cov           # With coverage report (must maintain ≥80%)
make lint               # ruff check --fix + ruff format + ty check
make check              # All pre-commit hooks

# Run single test:
uv run pytest tests/test_signal.py -v
uv run pytest tests/ -k "test_name" -v

# Run examples:
cd examples/todo && uv run wtfui dev --web    # Web mode at localhost:8000
cd examples/console && uv run wtfui dev       # TUI mode in terminal
```

**E2E tests run separately** (they install greenlet which re-enables GIL):
```bash
make test-e2e           # Isolated venv, never mix with unit tests
```

## Architecture Overview

WtfUI is a Python-only UI framework targeting Python 3.14+ No-GIL. It uses context managers for UI hierarchy (`with Flex():` not `Flex(child)`) and fine-grained reactivity via Signal/Effect/Computed.

### Core Reactivity (`src/wtfui/core/`)

```
Signal[T]     → Reactive state container, notifies subscribers on change
Effect        → Side effect that re-runs when tracked signals change
Computed[T]   → Derived value, lazy + cached, invalidates on dependency change
```

**Tracking mechanism**: When an Effect/Computed runs, it sets a thread-local (`_running_effect`/`_evaluating_computed`). Signal.value getter checks these and auto-subscribes.

**Thread safety**: All reactive primitives use `threading.Lock()` for No-GIL safety.

### Element System (`src/wtfui/core/element.py`)

Base `Element` class implements context manager protocol:
- `__enter__`: Pushes to parent's children list (via context stack)
- `__exit__`: Pops from context stack
- Elements never know how to render themselves (Bridge Pattern)

### Renderers (Bridge Pattern)

Platform-agnostic Element → Platform-specific output:

| Renderer | Location | Output |
|----------|----------|--------|
| `HTMLRenderer` | `web/renderer/html.py` | HTML strings (SSR) |
| `DOMRenderer` | `web/renderer/dom.py` | js.document calls (Wasm) |
| TUI Renderer | `tui/renderer/` | Terminal escape sequences |

### Compiler Pipeline (`src/wtfui/web/compiler/`)

Transforms Python to browser-runnable code:

```
app.py → AST analysis → transformer.py → wtfuibyte.py → opcodes → browser
                              ↓
                        @rpc functions stripped,
                        replaced with fetch stubs
```

Key files:
- `transformer.py` - AST transformation, @rpc stripping
- `wtfuibyte.py` - WtfUICompiler, bytecode generation
- `shaker.py` - Tree shaking unused code
- `linker.py` - Module resolution and bundling

### RPC System (`src/wtfui/web/rpc/`)

`@rpc` decorator marks server-only functions. In client bundle, body is replaced with `fetch()` stub. Server keeps full implementation.

### Layout Engine (`src/wtfui/tui/layout/`)

Yoga-compatible Flexbox implementation. See `src/wtfui/tui/layout/CLAUDE.md` for details.

**Parallel layout**: Nodes with explicit width+height are "layout boundaries" that can compute in parallel via `ThreadPoolExecutor` (No-GIL).

## Key Patterns

**UI hierarchy via context managers**:
```python
with Flex(direction="column"):
    with Box(padding=10):
        Text("Hello")  # Child of Box, grandchild of Flex
```

**Reactive updates**:
```python
count = Signal(0)
Effect(lambda: print(f"Count: {count.value}"))  # Auto-tracks count
count.value += 1  # Triggers effect
```

**Frozen dataclasses for thread safety** (e.g., `FlexStyle`):
```python
@dataclass(frozen=True, slots=True)
class FlexStyle: ...
```

## Conventions

- Python 3.14+ syntax, `class Signal[T]:` not `Generic[T]`
- Use `__slots__` for performance-critical classes
- Private methods: single underscore prefix
- Conventional commits enforced: `feat(scope): description`
- Line length: 100 chars
- Double quotes for strings

## Critical Warnings

1. **No greenlet in unit tests** - E2E tests install greenlet which re-enables GIL. Never run `make test-e2e` in same session as unit tests.

2. **Scheduler state** - Tests auto-reset via `conftest.py` fixture. If writing scheduler tests, call `reset_scheduler()` explicitly.

3. **Empty context managers** - Custom flake8 rule FLE001 catches `with Flex(): pass`. UI elements must have content.
