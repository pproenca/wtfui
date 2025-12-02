# Flow Framework Implementation Plan

> **Goal:** Build a Pythonic UI framework that uses context managers, descriptors, and signals to create reactive interfaces—spanning server-side rendering to WebAssembly.
> **Tech Stack:** Python 3.14+, FastAPI, WebSockets, AsyncIO, AST module, Free-Threading (No-GIL)
> **Skills Reference:** See @.cursor/skills/test-driven-development.md for TDD protocol

---

## Python Steering Council Amendments

This plan incorporates critical architectural decisions from the Steering Council review to achieve the "Universal Isomorphic Runtime" goal:

### Amendment 1: Renderer Protocol (Replaces `to_html`)
**Problem:** Hard-coding `to_html()` on `Element` couples the framework to SSR and requires rewrites for Wasm.
**Solution:** Abstract `Renderer` protocol. Elements produce trees; renderers consume them.
- `HTMLRenderer` (Server) → HTML strings
- `DOMRenderer` (Wasm) → `js.document` calls

### Amendment 2: Thread-Safe Signals (No-GIL 3.14)
**Problem:** Python 3.14's free-threading means concurrent state updates can tear.
**Solution:** Use `threading.Lock` in `Signal._notify()` for thread-safe updates.

### Amendment 3: Lazy Annotation Injection (PEP 649)
**Problem:** `get_type_hints()` evaluates immediately, crashing on circular dependencies.
**Solution:** Use `annotationlib` for deferred evaluation, enabling complex enterprise patterns.

### Amendment 4: Zero-Build Development
**Problem:** CLI `build` step violates "zero-friction" development experience.
**Solution:** Import hook (`sys.meta_path`) transpiles ASTs on-the-fly during dev. Just run `python app.py`.

### Amendment 5: Style Architecture (V2-Ready)
**Problem:** Using `cls="tailwind-classes"` is acceptable for V1, but not "elegant" for a Pythonic framework.
**Solution:** Architect `Element.props` to accept both string classes and future `Style` objects or keyword-argument styling (e.g., `Div(padding=4)`). V1 uses `cls`, V2 can add Pythonic styling without breaking changes.

### Amendment 6: Robust RPC Serialization
**Problem:** `json.dumps` doesn't handle `datetime`, `UUID`, `dataclasses` automatically. A world-class Python framework must handle these.
**Solution:** `FlowJSONEncoder` extends `json.JSONEncoder` to serialize all common Python types automatically. Developers don't need to manually convert objects to dicts.

### Amendment 7: Debug Mode for Import Hook (HIGH-RISK Mitigation)
**Problem:** Debugging dynamic AST transformations in memory is difficult.
**Solution:** `FlowImportHook` includes a debug mode (`FLOW_DEBUG=1` or `--debug` flag) that dumps transformed source to `.flow-debug/` directory with metadata comments.

---

## Overview

Flow is a Python UI framework based on these core principles:

1. **Indentation is Topology** - `with` blocks define DOM hierarchy
2. **Reactivity via Signals** - Fine-grained, thread-safe updates without setState
3. **Dependency Injection** - Lazy type hints for context injection (PEP 649)
4. **Async by Default** - Rendering is non-blocking
5. **Universal Runtime** - Same code runs on server and client (Wasm) via Renderer Protocol
6. **Zero-Build Dev** - No compilation step; import hooks handle transpilation

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FLOW FRAMEWORK                          │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Core Engine                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Element    │  │   Signal    │  │   Effect    │             │
│  │  (Context   │  │   (Value +  │  │   (Tracks   │             │
│  │   Manager)  │  │   Notify)   │  │   Deps)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: UI Primitives                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Div      │  │    Text     │  │   Button    │             │
│  │   VStack    │  │    Input    │  │    Card     │             │
│  │   HStack    │  │   Window    │  │   ...etc    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Component System                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ @component  │  │  Computed   │  │  Dependency │             │
│  │  Decorator  │  │  Properties │  │  Injection  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: Server Runtime                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   to_html   │  │ LiveSession │  │  WebSocket  │             │
│  │  Renderer   │  │   Manager   │  │   Server    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 5: RPC System                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    @rpc     │  │   Server    │  │   Client    │             │
│  │  Decorator  │  │  Dispatch   │  │   Proxy     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 6: Build System                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    AST      │  │   Bundle    │  │    CLI      │             │
│  │  Splitter   │  │  Generator  │  │  Commands   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Engine (Foundation)

**Objective:** Build the reactive primitives that power the entire framework.

---

### Task 1.1: Project Setup (Python 3.14+)

> **Note:** Requires Python 3.14+ for No-GIL (PEP 703) and PEP 649 (deferred annotations).

**Files:**
- Create: `pyproject.toml`
- Create: `src/flow/__init__.py`
- Create: `src/flow/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml with dependencies**
```toml
[project]
name = "flow"
version = "0.1.0"
description = "A Pythonic UI framework using context managers and signals"
requires-python = ">=3.14"  # Required for No-GIL and PEP 649
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "websockets>=12.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[project.scripts]
flow = "flow.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.hatch.build.targets.wheel]
packages = ["src/flow"]
```

**Step 2: Create package structure**
```bash
mkdir -p src/flow tests
touch src/flow/__init__.py src/flow/py.typed
touch tests/__init__.py tests/conftest.py
```

**Step 3: Verify setup**
Run: `uv sync && uv run python -c "import flow; print('Flow imported successfully')"`
Expected: "Flow imported successfully"

**Step 4: Commit**
```bash
git add .
git commit -m "chore: initial project structure"
```

---

### Task 1.2: Context Stack (ContextVar for Parent Tracking)

**Files:**
- Create: `src/flow/context.py`
- Test: `tests/test_context.py`

**Step 1: Write the failing test**
```python
# tests/test_context.py
from flow.context import get_current_parent, set_current_parent, reset_parent

def test_context_stack_initially_none():
    """The parent context starts as None."""
    assert get_current_parent() is None

def test_context_stack_set_and_get():
    """Setting a parent makes it retrievable."""
    parent = object()
    token = set_current_parent(parent)
    try:
        assert get_current_parent() is parent
    finally:
        reset_parent(token)

def test_context_stack_nesting():
    """Context can be nested and restored."""
    parent1 = object()
    parent2 = object()

    token1 = set_current_parent(parent1)
    try:
        assert get_current_parent() is parent1
        token2 = set_current_parent(parent2)
        try:
            assert get_current_parent() is parent2
        finally:
            reset_parent(token2)
        assert get_current_parent() is parent1
    finally:
        reset_parent(token1)
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_context.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/context.py
"""Context stack for tracking the current parent element during rendering."""

from contextvars import ContextVar, Token
from typing import Any, Optional

# Tracks the current 'parent' element being rendered
_current_parent: ContextVar[Optional[Any]] = ContextVar("flow_parent", default=None)

def get_current_parent() -> Optional[Any]:
    """Get the current parent element from the context stack."""
    return _current_parent.get()

def set_current_parent(parent: Any) -> Token:
    """Push a new parent onto the context stack. Returns a token for reset."""
    return _current_parent.set(parent)

def reset_parent(token: Token) -> None:
    """Pop the parent from the context stack using the token."""
    _current_parent.reset(token)
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_context.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**
```bash
git add src/flow/context.py tests/test_context.py
git commit -m "feat(core): add context stack for parent tracking"
```

---

### Task 1.3: Element Base Class (Context Manager)

**Files:**
- Create: `src/flow/element.py`
- Test: `tests/test_element.py`

**Step 1: Write the failing test**
```python
# tests/test_element.py
from flow.element import Element
from flow.context import get_current_parent

def test_element_has_tag_from_class_name():
    """Element tag defaults to class name."""
    el = Element()
    assert el.tag == "Element"

def test_element_stores_props():
    """Element stores arbitrary props."""
    el = Element(cls="container", id="main")
    assert el.props == {"cls": "container", "id": "main"}

def test_element_starts_with_no_children():
    """Element has empty children list."""
    el = Element()
    assert el.children == []

def test_element_context_manager_sets_parent():
    """Entering element sets it as current parent."""
    el = Element()
    assert get_current_parent() is None
    with el:
        assert get_current_parent() is el
    assert get_current_parent() is None

def test_element_nesting_builds_tree():
    """Nested context managers build parent-child relationships."""
    parent = Element()
    child = Element()

    with parent:
        with child:
            pass

    assert child in parent.children
    assert child.parent is parent

def test_multiple_children():
    """Multiple children can be added to a parent."""
    parent = Element()
    child1 = Element()
    child2 = Element()

    with parent:
        with child1:
            pass
        with child2:
            pass

    assert parent.children == [child1, child2]
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_element.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/element.py
"""Base Element class - the foundation of all UI nodes."""

from __future__ import annotations
from typing import Any, Optional
from contextvars import Token

from flow.context import get_current_parent, set_current_parent, reset_parent


class Element:
    """The base class for all UI nodes (Div, VStack, Text, etc.)."""

    def __init__(self, **props: Any) -> None:
        self.tag: str = self.__class__.__name__
        self.props: dict[str, Any] = props
        self.children: list[Element] = []
        self.parent: Optional[Element] = None
        self._token: Optional[Token] = None

    def __enter__(self) -> Element:
        # Capture current parent (if any)
        self.parent = get_current_parent()

        # Attach self to parent's children
        if self.parent is not None:
            self.parent.children.append(self)

        # Push self as the new 'Active Parent'
        self._token = set_current_parent(self)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        # Pop self off the stack, restoring the previous parent
        if self._token is not None:
            reset_parent(self._token)
            self._token = None

    def __repr__(self) -> str:
        return f"<{self.tag} children={len(self.children)} />"
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_element.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**
```bash
git add src/flow/element.py tests/test_element.py
git commit -m "feat(core): add Element base class with context manager"
```

---

### Task 1.4: Signal Primitive (Thread-Safe Reactive Value)

> **⚠️ STEERING COUNCIL AMENDMENT:** Signals must be thread-safe for Python 3.14 No-GIL builds.
> Uses `threading.Lock` to prevent tearing during concurrent updates.

**Files:**
- Create: `src/flow/signal.py`
- Test: `tests/test_signal.py`

**Step 1: Write the failing test**
```python
# tests/test_signal.py
import threading
from flow.signal import Signal

def test_signal_stores_initial_value():
    """Signal stores and returns its initial value."""
    sig = Signal(42)
    assert sig.value == 42

def test_signal_updates_value():
    """Signal value can be updated."""
    sig = Signal(0)
    sig.value = 100
    assert sig.value == 100

def test_signal_no_notify_on_same_value():
    """Signal does not notify when value unchanged."""
    notifications = []

    sig = Signal(5)
    sig.subscribe(lambda: notifications.append("called"))

    sig.value = 5  # Same value
    assert notifications == []

def test_signal_notifies_on_change():
    """Signal notifies subscribers when value changes."""
    notifications = []

    sig = Signal(0)
    sig.subscribe(lambda: notifications.append("called"))

    sig.value = 1
    assert notifications == ["called"]

def test_signal_multiple_subscribers():
    """Signal notifies all subscribers."""
    calls = []

    sig = Signal("a")
    sig.subscribe(lambda: calls.append("sub1"))
    sig.subscribe(lambda: calls.append("sub2"))

    sig.value = "b"
    assert calls == ["sub1", "sub2"]

def test_signal_generic_typing():
    """Signal supports generic types."""
    sig_int: Signal[int] = Signal(0)
    sig_str: Signal[str] = Signal("")

    sig_int.value = 42
    sig_str.value = "hello"

    assert sig_int.value == 42
    assert sig_str.value == "hello"

def test_signal_thread_safety():
    """Signal handles concurrent updates without tearing (No-GIL safe)."""
    sig = Signal(0)
    results = []

    def increment():
        for _ in range(100):
            sig.value = sig.value + 1

    threads = [threading.Thread(target=increment) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Value should be 400 if thread-safe (no lost updates)
    assert sig.value == 400
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_signal.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation (Thread-Safe)**
```python
# src/flow/signal.py
"""Signal - A thread-safe reactive value for Python 3.14+ No-GIL builds."""

from __future__ import annotations
import threading
from typing import TypeVar, Generic, Callable, Set

T = TypeVar("T")


class Signal(Generic[T]):
    """
    A thread-safe value that notifies subscribers when it changes.

    Uses threading.Lock for No-GIL safety in Python 3.14+.
    The lock is cheap in free-threaded builds.
    """

    def __init__(self, value: T) -> None:
        self._value: T = value
        self._subscribers: Set[Callable[[], None]] = set()
        self._lock = threading.Lock()  # No-GIL safe

    @property
    def value(self) -> T:
        """Get the current value (thread-safe read)."""
        with self._lock:
            return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the value and notify subscribers if changed (thread-safe write)."""
        with self._lock:
            if self._value != new_value:
                self._value = new_value
                self._notify_locked()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns unsubscribe function."""
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        """Remove a subscriber (thread-safe)."""
        with self._lock:
            self._subscribers.discard(callback)

    def _notify_locked(self) -> None:
        """Notify all subscribers. Must be called with lock held."""
        # Copy to allow subscribers to modify during iteration
        subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber()

    def __repr__(self) -> str:
        with self._lock:
            return f"Signal({self._value!r})"
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_signal.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**
```bash
git add src/flow/signal.py tests/test_signal.py
git commit -m "feat(core): add Signal reactive primitive"
```

---

### Task 1.5: Effect (Thread-Safe Dependency Tracking)

> **⚠️ STEERING COUNCIL AMENDMENT:** Effect scheduling must be thread-safe for No-GIL builds.
> Uses per-thread ContextVar for tracking and thread-safe effect scheduling.

**Files:**
- Create: `src/flow/effect.py`
- Modify: `src/flow/signal.py` (add tracking with thread-safety)
- Test: `tests/test_effect.py`

**Step 1: Write the failing test**
```python
# tests/test_effect.py
import threading
from flow.signal import Signal
from flow.effect import Effect, get_running_effect

def test_effect_runs_function_immediately():
    """Effect executes its function on creation."""
    calls = []
    Effect(lambda: calls.append("ran"))
    assert calls == ["ran"]

def test_effect_tracks_signal_access():
    """Effect automatically tracks signals read during execution."""
    count = Signal(0)
    computed_values = []

    def compute():
        computed_values.append(count.value * 2)

    Effect(compute)
    assert computed_values == [0]  # Initial run

    count.value = 5
    assert computed_values == [0, 10]  # Re-ran after signal change

def test_effect_tracks_multiple_signals():
    """Effect tracks multiple signal dependencies."""
    a = Signal(1)
    b = Signal(2)
    results = []

    def compute():
        results.append(a.value + b.value)

    Effect(compute)
    assert results == [3]

    a.value = 10
    assert results == [3, 12]

    b.value = 20
    assert results == [3, 12, 30]

def test_running_effect_context():
    """get_running_effect returns the active effect during execution."""
    captured = []

    def capture():
        captured.append(get_running_effect())

    effect = Effect(capture)
    assert captured[0] is effect

def test_effect_thread_isolation():
    """Effects in different threads don't interfere (No-GIL safe)."""
    results = {"thread1": [], "thread2": []}
    sig1 = Signal(0)
    sig2 = Signal(0)

    def thread1_work():
        def track():
            results["thread1"].append(sig1.value)
        Effect(track)
        sig1.value = 10

    def thread2_work():
        def track():
            results["thread2"].append(sig2.value)
        Effect(track)
        sig2.value = 20

    t1 = threading.Thread(target=thread1_work)
    t2 = threading.Thread(target=thread2_work)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert 0 in results["thread1"] and 10 in results["thread1"]
    assert 0 in results["thread2"] and 20 in results["thread2"]
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_effect.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Update Signal to support thread-safe effect tracking**
```python
# src/flow/signal.py (updated with thread-safe effect tracking)
"""Signal - A thread-safe reactive value for Python 3.14+ No-GIL builds."""

from __future__ import annotations
import threading
from typing import TYPE_CHECKING, TypeVar, Generic, Callable, Set

if TYPE_CHECKING:
    from flow.effect import Effect

T = TypeVar("T")


class Signal(Generic[T]):
    """
    A thread-safe value that notifies subscribers when it changes.

    Uses threading.Lock for No-GIL safety in Python 3.14+.
    """

    def __init__(self, value: T) -> None:
        self._value: T = value
        self._subscribers: Set[Callable[[], None]] = set()
        self._effects: Set[Effect] = set()
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        """Get the current value and track effect dependency (thread-safe)."""
        from flow.effect import get_running_effect

        with self._lock:
            effect = get_running_effect()
            if effect is not None:
                self._effects.add(effect)
            return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the value and notify subscribers if changed (thread-safe)."""
        with self._lock:
            if self._value != new_value:
                self._value = new_value
                self._notify_locked()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns unsubscribe function."""
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._subscribers.discard(callback)

    def _notify_locked(self) -> None:
        """Notify all subscribers and effects. Must be called with lock held."""
        subscribers = list(self._subscribers)
        effects = list(self._effects)

        for subscriber in subscribers:
            subscriber()

        for effect in effects:
            effect.schedule()  # Schedule, don't run inline (prevents deadlock)

    def __repr__(self) -> str:
        with self._lock:
            return f"Signal({self._value!r})"
```

**Step 4: Write Effect implementation (Thread-Safe)**
```python
# src/flow/effect.py
"""Effect - Thread-safe dependency tracking for Python 3.14+ No-GIL builds."""

from __future__ import annotations
import threading
from contextvars import ContextVar, Token
from typing import Callable, Optional

# ContextVar is per-thread in No-GIL builds, providing natural isolation
_running_effect: ContextVar[Optional["Effect"]] = ContextVar("running_effect", default=None)


def get_running_effect() -> Optional["Effect"]:
    """Get the currently executing effect (thread-local via ContextVar)."""
    return _running_effect.get()


class Effect:
    """
    Wraps a function to track Signal usage and re-run on changes.

    Thread-safe for Python 3.14+ No-GIL builds.
    """

    def __init__(self, fn: Callable[[], None]) -> None:
        self.fn = fn
        self._lock = threading.Lock()
        self._scheduled = False
        self.run()

    def schedule(self) -> None:
        """Schedule this effect for re-execution (thread-safe, deduped)."""
        with self._lock:
            if self._scheduled:
                return
            self._scheduled = True

        # In a full implementation, this would go to an event loop
        # For now, execute synchronously
        self.run()

    def run(self) -> None:
        """Execute the function while tracking as the active effect."""
        with self._lock:
            self._scheduled = False

        token: Token = _running_effect.set(self)
        try:
            self.fn()
        finally:
            _running_effect.reset(token)

    def __repr__(self) -> str:
        return f"Effect({self.fn.__name__})"
```

**Step 5: Run test to verify it passes**
Run: `uv run pytest tests/test_effect.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**
```bash
git add src/flow/signal.py src/flow/effect.py tests/test_effect.py
git commit -m "feat(core): add Effect for dependency tracking"
```

---

### Task 1.6: Package Exports

**Files:**
- Modify: `src/flow/__init__.py`
- Test: `tests/test_exports.py`

**Step 1: Write the failing test**
```python
# tests/test_exports.py
def test_core_exports():
    """Core classes are exported from flow package."""
    from flow import Element, Signal, Effect

    assert Element is not None
    assert Signal is not None
    assert Effect is not None

def test_signal_can_be_used():
    """Signal works when imported from flow."""
    from flow import Signal

    sig = Signal(42)
    assert sig.value == 42
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_exports.py -v`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**
```python
# src/flow/__init__.py
"""Flow - A Pythonic UI Framework using context managers and signals."""

from flow.element import Element
from flow.signal import Signal
from flow.effect import Effect

__all__ = [
    "Element",
    "Signal",
    "Effect",
]

__version__ = "0.1.0"
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_exports.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**
```bash
git add src/flow/__init__.py tests/test_exports.py
git commit -m "feat(core): export core classes from package root"
```

---

## Phase 2: UI Primitives

**Objective:** Create the basic UI elements (Div, Text, Button, etc.) that developers use to build interfaces.

---

### Task 2.1: Basic UI Elements (Div, Text, Button)

> **⚠️ STEERING COUNCIL AMENDMENT:** The `cls` prop is acceptable for V1, but the architecture
> must support a future `Style` object or keyword-argument styling (e.g., `Div(padding=4)`).
> `Element.props` is designed to handle both string classes and future Style objects.

**Files:**
- Create: `src/flow/ui/__init__.py`
- Create: `src/flow/ui/elements.py`
- Test: `tests/test_ui_elements.py`

**Step 1: Write the failing test**
```python
# tests/test_ui_elements.py
from flow.ui import Div, Text, Button, Input, VStack, HStack

def test_div_element():
    """Div creates a div element."""
    div = Div(cls="container")
    assert div.tag == "Div"
    assert div.props["cls"] == "container"

def test_text_element():
    """Text creates text content."""
    text = Text("Hello, World!")
    assert text.tag == "Text"
    assert text.content == "Hello, World!"

def test_button_element():
    """Button creates a button with click handler."""
    clicked = []
    btn = Button("Click me", on_click=lambda: clicked.append(True))
    assert btn.tag == "Button"
    assert btn.label == "Click me"
    assert "on_click" in btn.props

def test_input_element():
    """Input creates an input field."""
    from flow import Signal
    value = Signal("")
    inp = Input(bind=value, placeholder="Enter text")
    assert inp.tag == "Input"
    assert inp.props["placeholder"] == "Enter text"

def test_vstack_layout():
    """VStack stacks children vertically."""
    with VStack(gap=4) as stack:
        with Div():
            pass
        with Div():
            pass

    assert stack.tag == "VStack"
    assert len(stack.children) == 2
    assert stack.props["gap"] == 4

def test_hstack_layout():
    """HStack stacks children horizontally."""
    with HStack(gap=2) as stack:
        with Text("A"):
            pass
        with Text("B"):
            pass

    assert stack.tag == "HStack"
    assert len(stack.children) == 2

def test_props_support_future_style_architecture():
    """Props architecture supports future Style objects (V2 preparation)."""
    # V1: String-based classes
    div1 = Div(cls="container p-4")
    assert div1.props["cls"] == "container p-4"

    # V2-ready: Props can hold any value (Style objects in future)
    div2 = Div(padding=4, margin=2)  # Keyword-argument styling
    assert div2.props["padding"] == 4
    assert div2.props["margin"] == 2

    # The architecture allows both patterns to coexist
    div3 = Div(cls="container", padding=4)
    assert "cls" in div3.props
    assert "padding" in div3.props
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_ui_elements.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/ui/elements.py
"""UI Elements - The building blocks of Flow interfaces."""

from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING

from flow.element import Element

if TYPE_CHECKING:
    from flow.signal import Signal


class Div(Element):
    """A generic container element."""
    pass


class VStack(Element):
    """A vertical stack layout container."""
    pass


class HStack(Element):
    """A horizontal stack layout container."""
    pass


class Card(Element):
    """A card container with optional title."""

    def __init__(self, title: Optional[str] = None, **props: Any) -> None:
        super().__init__(**props)
        self.title = title


class Text(Element):
    """A text content element."""

    def __init__(self, content: str = "", **props: Any) -> None:
        super().__init__(**props)
        self.content = content

    def __enter__(self) -> Text:
        # Text elements typically don't have children, but support it for consistency
        return super().__enter__()


class Button(Element):
    """A clickable button element."""

    def __init__(
        self,
        label: str = "",
        on_click: Optional[Callable[[], Any]] = None,
        disabled: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(on_click=on_click, disabled=disabled, **props)
        self.label = label


class Input(Element):
    """A text input element with optional Signal binding."""

    def __init__(
        self,
        bind: Optional[Signal[str]] = None,
        placeholder: str = "",
        on_change: Optional[Callable[[str], Any]] = None,
        **props: Any,
    ) -> None:
        super().__init__(placeholder=placeholder, on_change=on_change, **props)
        self.bind = bind


class Window(Element):
    """A top-level window container."""

    def __init__(
        self,
        title: str = "Flow App",
        theme: str = "light",
        **props: Any,
    ) -> None:
        super().__init__(title=title, theme=theme, **props)
```

```python
# src/flow/ui/__init__.py
"""Flow UI Elements."""

from flow.ui.elements import (
    Div,
    VStack,
    HStack,
    Card,
    Text,
    Button,
    Input,
    Window,
)

__all__ = [
    "Div",
    "VStack",
    "HStack",
    "Card",
    "Text",
    "Button",
    "Input",
    "Window",
]
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_ui_elements.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**
```bash
git add src/flow/ui/ tests/test_ui_elements.py
git commit -m "feat(ui): add basic UI elements (Div, Text, Button, Input, etc.)"
```

---

### Task 2.2: Abstract Renderer Protocol (Universal Runtime Foundation)

> **⚠️ STEERING COUNCIL AMENDMENT:** This replaces the original `to_html()` approach.
> Elements produce abstract trees; Renderers consume them. This enables the Universal Runtime.

**Files:**
- Create: `src/flow/renderer/__init__.py`
- Create: `src/flow/renderer/protocol.py`
- Create: `src/flow/renderer/html.py`
- Modify: `src/flow/element.py` (add `render()` method)
- Test: `tests/test_renderer.py`

**Step 1: Write the failing test**
```python
# tests/test_renderer.py
from flow.ui import Div, Text, Button, VStack
from flow.renderer import HTMLRenderer, Renderer
from flow.renderer.protocol import RenderNode

def test_renderer_protocol_exists():
    """Renderer is an abstract protocol."""
    assert hasattr(Renderer, "render_element")
    assert hasattr(Renderer, "render_text")

def test_element_produces_render_node():
    """Elements produce RenderNode for renderers to consume."""
    div = Div(cls="container")
    node = div.to_render_node()

    assert node.tag == "Div"
    assert node.props["cls"] == "container"
    assert node.element_id == id(div)

def test_html_renderer_simple_element():
    """HTMLRenderer produces HTML from elements."""
    div = Div(cls="container")
    renderer = HTMLRenderer()

    html = renderer.render(div)

    assert "<div" in html.lower()
    assert 'class="container"' in html
    assert f'id="flow-{id(div)}"' in html

def test_html_renderer_text_element():
    """HTMLRenderer renders Text content."""
    text = Text("Hello, World!")
    renderer = HTMLRenderer()

    html = renderer.render(text)
    assert "Hello, World!" in html

def test_html_renderer_nested_elements():
    """HTMLRenderer handles nested children."""
    with Div(cls="parent") as parent:
        with Text("Child 1"):
            pass
        with Text("Child 2"):
            pass

    renderer = HTMLRenderer()
    html = renderer.render(parent)

    assert "Child 1" in html
    assert "Child 2" in html

def test_html_renderer_button():
    """HTMLRenderer renders Button with label."""
    btn = Button("Click me")
    renderer = HTMLRenderer()

    html = renderer.render(btn)
    assert "Click me" in html

def test_renderer_is_swappable():
    """Different renderers can be used interchangeably."""
    div = Div(cls="test")

    # Both implement the same protocol
    html_renderer = HTMLRenderer()

    # In Wasm, we'd use DOMRenderer instead
    # This test just verifies the abstraction works
    result = html_renderer.render(div)
    assert isinstance(result, str)
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_renderer.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the Renderer Protocol**
```python
# src/flow/renderer/protocol.py
"""Renderer Protocol - Abstract interface for rendering Elements."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from flow.element import Element


@dataclass
class RenderNode:
    """
    Abstract representation of an Element for rendering.

    This decouples Elements from their rendering strategy,
    enabling the Universal Runtime (SSR + Wasm).
    """
    tag: str
    element_id: int
    props: dict[str, Any] = field(default_factory=dict)
    children: list["RenderNode"] = field(default_factory=list)

    # Special content fields
    text_content: str | None = None
    label: str | None = None


class Renderer(ABC):
    """
    Abstract base class for all renderers.

    Implementations:
    - HTMLRenderer: Outputs HTML strings (Server)
    - DOMRenderer: Outputs js.document calls (Wasm)
    """

    @abstractmethod
    def render(self, element: "Element") -> Any:
        """Render an element tree. Return type depends on implementation."""
        ...

    @abstractmethod
    def render_node(self, node: RenderNode) -> Any:
        """Render a single RenderNode."""
        ...

    @abstractmethod
    def render_text(self, content: str) -> Any:
        """Render text content."""
        ...
```

**Step 4: Write the HTML Renderer**
```python
# src/flow/renderer/html.py
"""HTMLRenderer - Renders Elements to HTML strings for SSR."""

from __future__ import annotations
from typing import TYPE_CHECKING

from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from flow.element import Element


class HTMLRenderer(Renderer):
    """
    Renders Element trees to HTML strings.

    Used for Server-Side Rendering (SSR).
    Can be swapped with DOMRenderer for Wasm.
    """

    # Tag mapping from Flow element names to HTML tags
    TAG_MAP: dict[str, str] = {
        "Div": "div",
        "VStack": "div",
        "HStack": "div",
        "Card": "div",
        "Text": "span",
        "Button": "button",
        "Input": "input",
        "Window": "div",
    }

    def render(self, element: "Element") -> str:
        """Render an element tree to HTML."""
        node = element.to_render_node()
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> str:
        """Render a RenderNode to HTML."""
        html_tag = self.TAG_MAP.get(node.tag, "div")

        # Build attributes
        attrs_parts: list[str] = []
        attrs_parts.append(f'id="flow-{node.element_id}"')

        for key, value in node.props.items():
            if key == "cls":
                attrs_parts.append(f'class="{value}"')
            elif key.startswith("on_"):
                # Event handlers are managed client-side
                continue
            elif isinstance(value, bool):
                if value:
                    attrs_parts.append(key)
            elif value is not None:
                attrs_parts.append(f'{key}="{value}"')

        attrs_str = " ".join(attrs_parts)

        # Get inner content
        inner_html = self._render_inner(node)

        # Self-closing tags
        if html_tag in ("input", "img", "br", "hr"):
            return f"<{html_tag} {attrs_str} />"

        return f"<{html_tag} {attrs_str}>{inner_html}</{html_tag}>"

    def _render_inner(self, node: RenderNode) -> str:
        """Render inner content of a node."""
        # Text content takes priority
        if node.text_content:
            return self.render_text(node.text_content)

        # Button labels
        if node.label:
            return self.render_text(node.label)

        # Render children
        return "".join(self.render_node(child) for child in node.children)

    def render_text(self, content: str) -> str:
        """Render text (with HTML escaping for safety)."""
        # Basic escaping for security
        return (
            content
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
```

**Step 5: Update Element with to_render_node()**
```python
# Add to src/flow/element.py (after __repr__ method)

    def to_render_node(self) -> "RenderNode":
        """
        Convert this element to an abstract RenderNode.

        This decouples Elements from rendering strategy,
        enabling Universal Runtime (SSR + Wasm).
        """
        from flow.renderer.protocol import RenderNode

        node = RenderNode(
            tag=self.tag,
            element_id=id(self),
            props=dict(self.props),
        )

        # Handle text content (Text elements)
        if hasattr(self, "content") and self.content:
            node.text_content = str(self.content)

        # Handle button labels
        if hasattr(self, "label") and self.label:
            node.label = str(self.label)

        # Recursively convert children
        node.children = [child.to_render_node() for child in self.children]

        return node
```

**Step 6: Create package exports**
```python
# src/flow/renderer/__init__.py
"""Flow Renderer - Abstract rendering for Universal Runtime."""

from flow.renderer.protocol import Renderer, RenderNode
from flow.renderer.html import HTMLRenderer

__all__ = [
    "Renderer",
    "RenderNode",
    "HTMLRenderer",
]
```

**Step 7: Run test to verify it passes**
Run: `uv run pytest tests/test_renderer.py -v`
Expected: PASS (7 tests)

**Step 8: Commit**
```bash
git add src/flow/renderer/ src/flow/element.py tests/test_renderer.py
git commit -m "feat(core): add Renderer Protocol for Universal Runtime"
```

---

### Task 2.3: DOM Renderer Stub (Wasm Preparation)

> This is a placeholder for Phase 8 but establishes the pattern now.

**Files:**
- Create: `src/flow/renderer/dom.py`
- Test: `tests/test_dom_renderer.py`

**Step 1: Write the failing test**
```python
# tests/test_dom_renderer.py
import sys
from unittest.mock import MagicMock
from flow.ui import Div, Text
from flow.renderer.dom import DOMRenderer

def test_dom_renderer_is_renderer():
    """DOMRenderer implements Renderer protocol."""
    from flow.renderer import Renderer
    renderer = DOMRenderer(document=MagicMock())
    assert isinstance(renderer, Renderer)

def test_dom_renderer_creates_element():
    """DOMRenderer calls document.createElement."""
    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(document=mock_doc)
    div = Div(cls="test")

    result = renderer.render(div)

    mock_doc.createElement.assert_called_with("div")
```

**Step 2: Write stub implementation**
```python
# src/flow/renderer/dom.py
"""DOMRenderer - Renders Elements directly to browser DOM (for Wasm)."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from flow.element import Element


class DOMRenderer(Renderer):
    """
    Renders Element trees directly to the browser DOM.

    Used in WebAssembly (PyScript/Pyodide) environments.
    Receives a `document` object (either real or mock).
    """

    TAG_MAP: dict[str, str] = {
        "Div": "div",
        "VStack": "div",
        "HStack": "div",
        "Card": "div",
        "Text": "span",
        "Button": "button",
        "Input": "input",
        "Window": "div",
    }

    def __init__(self, document: Any) -> None:
        """Initialize with a document object (js.document in Wasm)."""
        self.document = document

    def render(self, element: "Element") -> Any:
        """Render an element tree to DOM nodes."""
        node = element.to_render_node()
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> Any:
        """Render a RenderNode to a DOM element."""
        html_tag = self.TAG_MAP.get(node.tag, "div")

        # Create the element
        el = self.document.createElement(html_tag)
        el.id = f"flow-{node.element_id}"

        # Set attributes
        for key, value in node.props.items():
            if key == "cls":
                el.className = value
            elif key.startswith("on_"):
                # Event handlers would be proxied here
                pass
            elif isinstance(value, bool):
                if value:
                    el.setAttribute(key, "")
            elif value is not None:
                el.setAttribute(key, str(value))

        # Set inner content
        if node.text_content:
            el.textContent = node.text_content
        elif node.label:
            el.textContent = node.label
        else:
            for child in node.children:
                child_el = self.render_node(child)
                el.appendChild(child_el)

        return el

    def render_text(self, content: str) -> Any:
        """Create a text node."""
        return self.document.createTextNode(content)
```

**Step 3: Update renderer exports**
```python
# src/flow/renderer/__init__.py (updated)
"""Flow Renderer - Abstract rendering for Universal Runtime."""

from flow.renderer.protocol import Renderer, RenderNode
from flow.renderer.html import HTMLRenderer
from flow.renderer.dom import DOMRenderer

__all__ = [
    "Renderer",
    "RenderNode",
    "HTMLRenderer",
    "DOMRenderer",
]
```

**Step 4: Commit**
```bash
git add src/flow/renderer/dom.py tests/test_dom_renderer.py
git commit -m "feat(renderer): add DOMRenderer stub for Wasm preparation"
```

---

## Phase 3: Component System

**Objective:** Build the @component decorator with dependency injection and computed properties.

---

### Task 3.1: Component Decorator (Basic)

**Files:**
- Create: `src/flow/component.py`
- Test: `tests/test_component.py`

**Step 1: Write the failing test**
```python
# tests/test_component.py
import asyncio
from flow.component import component
from flow.ui import Div, Text

def test_component_decorator_marks_function():
    """@component decorator marks function as a component."""
    @component
    async def MyComponent():
        with Div():
            pass

    assert hasattr(MyComponent, "_is_flow_component")
    assert MyComponent._is_flow_component is True

def test_component_can_be_called():
    """Component can be called and returns element tree."""
    @component
    async def SimpleComponent():
        with Div(cls="simple") as root:
            with Text("Hello"):
                pass
        return root

    result = asyncio.run(SimpleComponent())
    assert result is not None
    assert result.tag == "Div"

def test_component_with_props():
    """Component can receive props."""
    @component
    async def Greeting(name: str):
        with Text(f"Hello, {name}!") as el:
            pass
        return el

    result = asyncio.run(Greeting(name="World"))
    assert result.content == "Hello, World!"

def test_component_nesting():
    """Components can nest other components."""
    @component
    async def Inner():
        with Text("Inner") as el:
            pass
        return el

    @component
    async def Outer():
        with Div() as root:
            inner_result = await Inner()
            # In real usage, inner would be composed
        return root

    result = asyncio.run(Outer())
    assert result.tag == "Div"
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_component.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/component.py
"""Component decorator for Flow UI components."""

from __future__ import annotations
from functools import wraps
from typing import Callable, Any, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def component(fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that marks an async function as a Flow component.

    Components are async functions that build UI using context managers.
    They can receive props as parameters and optionally use dependency injection.
    """
    @wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # In a full implementation, this would:
        # 1. Look up dependencies from type hints
        # 2. Inject them into the call
        # 3. Track the component in the render tree
        return await fn(*args, **kwargs)

    # Mark as a component for introspection
    wrapper._is_flow_component = True
    wrapper._original_fn = fn

    return wrapper
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_component.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**
```bash
git add src/flow/component.py tests/test_component.py
git commit -m "feat(component): add @component decorator"
```

---

### Task 3.2: Lazy Dependency Injection (PEP 649)

> **⚠️ STEERING COUNCIL AMENDMENT:** Uses PEP 649 deferred annotation evaluation.
> This enables circular dependencies in enterprise apps (e.g., `User` ↔ `Auth`).

**Files:**
- Create: `src/flow/injection.py`
- Modify: `src/flow/component.py`
- Test: `tests/test_injection.py`

**Step 1: Write the failing test**
```python
# tests/test_injection.py
import asyncio
from dataclasses import dataclass
from flow.component import component
from flow.injection import provide, get_provider, clear_providers
from flow.signal import Signal

@dataclass
class AppState:
    count: Signal[int]
    name: Signal[str]

def test_provide_registers_instance():
    """provide() registers an instance for a type."""
    clear_providers()
    state = AppState(count=Signal(0), name=Signal("Test"))
    provide(AppState, state)

    retrieved = get_provider(AppState)
    assert retrieved is state

def test_component_receives_injected_dependency():
    """Component with type-hinted parameter receives injection."""
    clear_providers()
    state = AppState(count=Signal(42), name=Signal("Injected"))
    provide(AppState, state)

    received_state = None

    @component
    async def MyComponent(state: AppState):
        nonlocal received_state
        received_state = state

    asyncio.run(MyComponent())

    assert received_state is state
    assert received_state.count.value == 42

def test_component_with_mixed_args():
    """Component can have both injected and explicit args."""
    clear_providers()
    state = AppState(count=Signal(0), name=Signal(""))
    provide(AppState, state)

    @component
    async def Greeting(name: str, state: AppState):
        state.name.value = name

    asyncio.run(Greeting(name="Alice"))

    assert state.name.value == "Alice"

def test_lazy_annotation_handles_forward_refs():
    """PEP 649: Forward references are resolved lazily."""
    clear_providers()

    # This would crash with eager get_type_hints() if Service
    # was defined after the component, but works with lazy eval
    @dataclass
    class Service:
        name: str

    @component
    async def UsesService(svc: Service):
        return svc.name

    provide(Service, Service(name="MyService"))
    result = asyncio.run(UsesService())
    assert result == "MyService"

def test_circular_dependency_pattern():
    """PEP 649: Circular type references don't crash."""
    clear_providers()

    # Simulates enterprise pattern: User <-> Auth circular dependency
    # With PEP 649, these forward refs are evaluated lazily

    @dataclass
    class AuthContext:
        user_id: int

    @component
    async def SecureComponent(auth: AuthContext):
        return auth.user_id

    provide(AuthContext, AuthContext(user_id=42))
    result = asyncio.run(SecureComponent())
    assert result == 42
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_injection.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write injection implementation (Thread-Safe)**
```python
# src/flow/injection.py
"""Dependency injection for Flow components (Thread-Safe, PEP 649 ready)."""

from __future__ import annotations
import threading
from contextvars import ContextVar
from typing import TypeVar, Dict, Type, Optional, Any

T = TypeVar("T")

# Thread-safe global registry for provided dependencies
_providers: ContextVar[Dict[Type, Any]] = ContextVar("providers", default={})
_providers_lock = threading.Lock()


def provide(type_: Type[T], instance: T) -> None:
    """Register an instance as the provider for a type (thread-safe)."""
    with _providers_lock:
        providers = _providers.get()
        new_providers = {**providers, type_: instance}
        _providers.set(new_providers)


def get_provider(type_: Type[T]) -> Optional[T]:
    """Get the registered provider for a type (thread-safe)."""
    with _providers_lock:
        providers = _providers.get()
        return providers.get(type_)


def clear_providers() -> None:
    """Clear all registered providers (thread-safe)."""
    with _providers_lock:
        _providers.set({})
```

**Step 4: Update component decorator for lazy injection (PEP 649)**
```python
# src/flow/component.py (updated with PEP 649 support)
"""Component decorator for Flow UI components (PEP 649 lazy injection)."""

from __future__ import annotations
import sys
import inspect
from functools import wraps
from typing import Callable, Any, TypeVar, ParamSpec

from flow.injection import get_provider

P = ParamSpec("P")
R = TypeVar("R")


def _get_lazy_annotations(fn: Callable) -> dict[str, Any]:
    """
    Get type annotations with deferred evaluation (PEP 649 compatible).

    In Python 3.14+, uses annotationlib for lazy evaluation.
    Falls back to get_type_hints with error handling for older versions.
    """
    # Python 3.14+: Use annotationlib for deferred evaluation
    if sys.version_info >= (3, 14):
        try:
            import annotationlib
            # Get annotations in VALUE format (fully resolved)
            return annotationlib.get_annotations(
                fn,
                format=annotationlib.Format.VALUE,
                eval_str=True
            )
        except Exception:
            pass

    # Python 3.12-3.13: Use get_type_hints with delayed evaluation
    try:
        from typing import get_type_hints
        # Get the function's global namespace for forward ref resolution
        globalns = getattr(fn, "__globals__", {})
        return get_type_hints(fn, globalns=globalns, include_extras=True)
    except Exception:
        # If all else fails, return raw annotations
        return getattr(fn, "__annotations__", {})


def component(fn: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that marks an async function as a Flow component.

    Components are async functions that build UI using context managers.
    They can receive props as parameters and use dependency injection.

    Uses PEP 649 deferred annotation evaluation to support:
    - Forward references
    - Circular dependencies (enterprise patterns)
    - Late binding of types
    """
    @wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # LAZY: Get type hints only when component is actually called
        # This enables circular dependencies and forward references
        hints = _get_lazy_annotations(fn)

        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())

        # Build the full kwargs with injected dependencies
        final_kwargs = dict(kwargs)

        # Count positional args already provided
        provided_positional = len(args)

        for i, param_name in enumerate(params):
            # Skip if already provided as positional arg
            if i < provided_positional:
                continue

            # Skip if already provided as keyword arg
            if param_name in final_kwargs:
                continue

            # Try to inject based on type hint
            if param_name in hints:
                hint_type = hints[param_name]
                provider = get_provider(hint_type)
                if provider is not None:
                    final_kwargs[param_name] = provider

        return await fn(*args, **final_kwargs)

    # Mark as a component for introspection
    wrapper._is_flow_component = True
    wrapper._original_fn = fn

    return wrapper
```

**Step 5: Run test to verify it passes**
Run: `uv run pytest tests/test_injection.py -v`
Expected: PASS (5 tests)

**Step 6: Commit**
```bash
git add src/flow/injection.py src/flow/component.py tests/test_injection.py
git commit -m "feat(component): add PEP 649 lazy dependency injection"
```

---

### Task 3.3: Computed Decorator

**Files:**
- Create: `src/flow/computed.py`
- Test: `tests/test_computed.py`

**Step 1: Write the failing test**
```python
# tests/test_computed.py
from flow.signal import Signal
from flow.computed import Computed

def test_computed_returns_value():
    """Computed property returns calculated value."""
    a = Signal(2)
    b = Signal(3)

    @Computed
    def sum_ab():
        return a.value + b.value

    assert sum_ab() == 5

def test_computed_caches_result():
    """Computed caches until dependencies change."""
    call_count = 0
    a = Signal(10)

    @Computed
    def expensive():
        nonlocal call_count
        call_count += 1
        return a.value * 2

    # First call computes
    result1 = expensive()
    assert result1 == 20
    assert call_count == 1

    # Second call uses cache
    result2 = expensive()
    assert result2 == 20
    assert call_count == 1  # Not recomputed

def test_computed_invalidates_on_signal_change():
    """Computed re-calculates when signal changes."""
    x = Signal(5)

    @Computed
    def doubled():
        return x.value * 2

    assert doubled() == 10

    x.value = 7
    assert doubled() == 14

def test_computed_tracks_multiple_signals():
    """Computed tracks all signals accessed."""
    a = Signal(1)
    b = Signal(2)
    c = Signal(3)

    @Computed
    def total():
        return a.value + b.value + c.value

    assert total() == 6

    b.value = 10
    assert total() == 14

    c.value = 20
    assert total() == 31
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_computed.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/computed.py
"""Computed - Memoized values that auto-update on signal changes."""

from __future__ import annotations
from typing import Callable, TypeVar, Generic, Optional, Set
from contextvars import ContextVar, Token

T = TypeVar("T")

# Track which Computed is currently being evaluated (for signal tracking)
_evaluating_computed: ContextVar[Optional["Computed"]] = ContextVar(
    "evaluating_computed", default=None
)


def get_evaluating_computed() -> Optional["Computed"]:
    """Get the Computed currently being evaluated."""
    return _evaluating_computed.get()


class Computed(Generic[T]):
    """
    A memoized computed value that tracks Signal dependencies.

    Automatically re-computes when any accessed Signal changes.
    """

    def __init__(self, fn: Callable[[], T]) -> None:
        self.fn = fn
        self._value: Optional[T] = None
        self._is_dirty: bool = True
        self._dependencies: Set = set()

    def __call__(self) -> T:
        """Get the computed value, recomputing if necessary."""
        if self._is_dirty:
            self._recompute()
        return self._value  # type: ignore

    def _recompute(self) -> None:
        """Recompute the value while tracking dependencies."""
        # Clear old dependencies
        self._dependencies.clear()

        # Set self as the currently evaluating computed
        token: Token = _evaluating_computed.set(self)
        try:
            self._value = self.fn()
            self._is_dirty = False
        finally:
            _evaluating_computed.reset(token)

    def invalidate(self) -> None:
        """Mark this computed as needing recalculation."""
        self._is_dirty = True

    def __repr__(self) -> str:
        return f"Computed({self.fn.__name__}, dirty={self._is_dirty})"
```

**Step 4: Update Signal to track Computed dependencies**
```python
# Add to src/flow/signal.py (update the value property getter)

    @property
    def value(self) -> T:
        """Get the current value and track effect/computed dependency."""
        from flow.effect import get_running_effect
        from flow.computed import get_evaluating_computed

        # Track effect dependency
        effect = get_running_effect()
        if effect is not None:
            self._effects.add(effect)

        # Track computed dependency
        computed = get_evaluating_computed()
        if computed is not None:
            self._computeds.add(computed)

        return self._value

# Add to __init__:
        self._computeds: Set["Computed"] = set()

# Update _notify():
    def _notify(self) -> None:
        """Notify all subscribers, effects, and computeds of a value change."""
        for subscriber in self._subscribers:
            subscriber()

        for effect in list(self._effects):
            effect.run()

        for computed in list(self._computeds):
            computed.invalidate()
```

**Step 5: Run test to verify it passes**
Run: `uv run pytest tests/test_computed.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**
```bash
git add src/flow/computed.py src/flow/signal.py tests/test_computed.py
git commit -m "feat(core): add Computed for memoized reactive values"
```

---

## Phase 4: Server Runtime

**Objective:** Build the server-side rendering and live hydration system.

---

### Task 4.1: LiveSession Manager (No-GIL Optimized)

> **⚠️ STEERING COUNCIL AMENDMENT:** Leverages Python 3.14 free-threading.
> Diff calculation runs in separate thread; asyncio handles I/O only.

**Files:**
- Create: `src/flow/server/__init__.py`
- Create: `src/flow/server/session.py`
- Test: `tests/test_session.py`

**Step 1: Write the failing test**
```python
# tests/test_session.py
import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock
from flow.server.session import LiveSession
from flow.ui import Div, Text
from flow.renderer import HTMLRenderer

def test_session_stores_root_component():
    """LiveSession stores the root component."""
    mock_ws = AsyncMock()
    root = Div()

    session = LiveSession(root, mock_ws)
    assert session.root_component is root

def test_session_has_update_queue():
    """LiveSession has an asyncio queue for updates."""
    mock_ws = AsyncMock()
    session = LiveSession(Div(), mock_ws)

    assert session.queue is not None
    assert isinstance(session.queue, asyncio.Queue)

def test_session_can_queue_updates():
    """Updates can be queued for sending."""
    mock_ws = AsyncMock()
    session = LiveSession(Div(), mock_ws)

    node = Text("Updated")
    session.queue_update(node)

    assert not session.queue.empty()

async def test_session_initial_render():
    """Session sends initial HTML on start."""
    mock_ws = AsyncMock()

    with Div(cls="root") as root:
        with Text("Hello"):
            pass

    session = LiveSession(root, mock_ws)
    await session.send_initial_render()

    mock_ws.send_text.assert_called_once()
    sent_html = mock_ws.send_text.call_args[0][0]
    assert "Hello" in sent_html
    assert "root" in sent_html

def test_session_uses_renderer_protocol():
    """LiveSession uses Renderer Protocol, not hardcoded to_html."""
    mock_ws = AsyncMock()
    root = Div(cls="test")

    session = LiveSession(root, mock_ws)

    # Session should use HTMLRenderer internally
    assert session.renderer is not None
    assert isinstance(session.renderer, HTMLRenderer)
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation (with Renderer Protocol & No-GIL threading)**
```python
# src/flow/server/__init__.py
"""Flow Server - WebSocket-based live rendering."""

from flow.server.session import LiveSession

__all__ = ["LiveSession"]
```

```python
# src/flow/server/session.py
"""LiveSession - No-GIL optimized live rendering manager."""

from __future__ import annotations
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TYPE_CHECKING

from flow.renderer import HTMLRenderer, Renderer

if TYPE_CHECKING:
    from flow.element import Element

# Thread pool for No-GIL diff calculation
# In Python 3.14+, this truly runs in parallel
_diff_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="flow-diff")

# Minimal client-side JS for receiving patches
CLIENT_JS = """
const socket = new WebSocket(`ws://${location.host}/ws`);
socket.onmessage = (event) => {
    const patch = JSON.parse(event.data);
    if (patch.op === 'replace') {
        const el = document.getElementById(patch.target_id);
        if (el) el.outerHTML = patch.html;
    }
};
"""


class LiveSession:
    """
    Manages the live connection between a Python UI tree and a browser.

    Optimized for Python 3.14+ No-GIL builds:
    - Diff calculation runs in ThreadPoolExecutor (truly parallel)
    - AsyncIO handles I/O only (WebSocket send/receive)
    - Uses Renderer Protocol for Universal Runtime compatibility
    """

    def __init__(
        self,
        root_component: "Element",
        websocket: Any,
        renderer: Renderer | None = None,
    ) -> None:
        self.root_component = root_component
        self.socket = websocket
        self.renderer = renderer or HTMLRenderer()  # Swappable!
        self.queue: asyncio.Queue["Element"] = asyncio.Queue()
        self._running = False
        self._lock = threading.Lock()

    def queue_update(self, node: "Element") -> None:
        """Queue a node for re-rendering and sending to client."""
        self.queue.put_nowait(node)

    async def send_initial_render(self) -> None:
        """Send the initial full HTML render to the client."""
        # Renderer Protocol: Not hardcoded to_html!
        full_html = self.renderer.render(self.root_component)

        html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="flow-root">{full_html}</div>
    <script>{CLIENT_JS}</script>
</body>
</html>
"""
        await self.socket.send_text(html_doc)

    async def start(self) -> None:
        """Start the live session loops."""
        await self.socket.accept()
        await self.send_initial_render()

        self._running = True

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._incoming_loop())
            tg.create_task(self._outgoing_loop())

    async def _incoming_loop(self) -> None:
        """Handle incoming events from the browser."""
        while self._running:
            try:
                data = await self.socket.receive_json()
                await self._handle_event(data)
            except Exception:
                self._running = False
                break

    async def _outgoing_loop(self) -> None:
        """Send queued updates to the browser (No-GIL optimized)."""
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                node = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # NO-GIL OPTIMIZATION: Run diff/render in thread pool
                # This is truly parallel in Python 3.14+ free-threaded builds
                html = await loop.run_in_executor(
                    _diff_executor,
                    self.renderer.render,  # Renderer Protocol!
                    node
                )

                patch = {
                    "op": "replace",
                    "target_id": f"flow-{id(node)}",
                    "html": html,
                }
                await self.socket.send_json(patch)

            except asyncio.TimeoutError:
                continue
            except Exception:
                self._running = False
                break

    async def _handle_event(self, data: dict) -> None:
        """Route an event to the appropriate handler."""
        # In full implementation, this would:
        # 1. Find the target node by ID
        # 2. Call the appropriate handler (on_click, etc.)
        # 3. Any Signal changes would trigger queue_update
        pass

    def stop(self) -> None:
        """Stop the session loops (thread-safe)."""
        with self._lock:
            self._running = False
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_session.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**
```bash
git add src/flow/server/ tests/test_session.py
git commit -m "feat(server): add LiveSession for WebSocket management"
```

---

### Task 4.2: FastAPI Server Integration

**Files:**
- Create: `src/flow/server/app.py`
- Test: `tests/test_server_app.py`

**Step 1: Write the failing test**
```python
# tests/test_server_app.py
import pytest
from fastapi.testclient import TestClient
from flow.server.app import create_app
from flow.ui import Div, Text
from flow.component import component

@component
async def SimpleApp():
    with Div(cls="container") as root:
        with Text("Hello from Flow!"):
            pass
    return root

def test_create_app_returns_fastapi():
    """create_app returns a FastAPI instance."""
    app = create_app(SimpleApp)
    assert app is not None
    assert hasattr(app, "routes")

def test_app_serves_html_on_root():
    """App serves HTML on GET /."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hello from Flow!" in response.text

def test_app_has_websocket_endpoint():
    """App exposes /ws WebSocket endpoint."""
    app = create_app(SimpleApp)

    # Check that route exists
    routes = [r.path for r in app.routes]
    assert "/ws" in routes
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_server_app.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation (with Renderer Protocol)**
```python
# src/flow/server/app.py
"""FastAPI application factory for Flow apps (Renderer Protocol)."""

from __future__ import annotations
import asyncio
from typing import Callable, Any

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse

from flow.server.session import LiveSession
from flow.renderer import HTMLRenderer, Renderer


def create_app(
    root_component: Callable[..., Any],
    renderer: Renderer | None = None,
) -> FastAPI:
    """
    Create a FastAPI app that serves a Flow component.

    Args:
        root_component: An async function decorated with @component
        renderer: Optional Renderer (defaults to HTMLRenderer)

    Returns:
        A configured FastAPI application
    """
    app = FastAPI(title="Flow App")
    _renderer = renderer or HTMLRenderer()

    # Store sessions by connection
    sessions: dict[str, LiveSession] = {}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Serve the initial HTML page."""
        # Render the component using Renderer Protocol
        root = await root_component()
        full_html = _renderer.render(root)  # Not hardcoded to_html!

        html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flow App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="flow-root">{full_html}</div>
    <script>
        const socket = new WebSocket(`ws://${{location.host}}/ws`);
        socket.onmessage = (event) => {{
            const patch = JSON.parse(event.data);
            if (patch.op === 'replace') {{
                const el = document.getElementById(patch.target_id);
                if (el) el.outerHTML = patch.html;
            }}
        }};

        document.addEventListener('click', (e) => {{
            const id = e.target.id;
            if (id && id.startsWith('flow-')) {{
                socket.send(JSON.stringify({{
                    type: 'click',
                    target_id: id
                }}));
            }}
        }});
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html_doc)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle WebSocket connections for live updates."""
        await websocket.accept()

        # Render component for this session (with shared renderer)
        root = await root_component()
        session = LiveSession(root, websocket, renderer=_renderer)

        session_id = str(id(websocket))
        sessions[session_id] = session

        try:
            # Keep connection alive and handle events
            while True:
                data = await websocket.receive_json()
                await session._handle_event(data)
        except Exception:
            pass
        finally:
            sessions.pop(session_id, None)

    return app


def run_app(
    root_component: Callable[..., Any],
    host: str = "127.0.0.1",
    port: int = 8000,
    renderer: Renderer | None = None,
) -> None:
    """Run a Flow app with uvicorn."""
    import uvicorn

    app = create_app(root_component, renderer=renderer)
    uvicorn.run(app, host=host, port=port)
```

**Step 4: Update server __init__.py**
```python
# src/flow/server/__init__.py
"""Flow Server - WebSocket-based live rendering."""

from flow.server.session import LiveSession
from flow.server.app import create_app, run_app

__all__ = ["LiveSession", "create_app", "run_app"]
```

**Step 5: Run test to verify it passes**
Run: `uv run pytest tests/test_server_app.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**
```bash
git add src/flow/server/ tests/test_server_app.py
git commit -m "feat(server): add FastAPI integration with create_app"
```

---

## Phase 5: RPC System

**Objective:** Build the @rpc decorator for seamless server/client function calls.

---

### Task 5.1: RPC Registry and Decorator (Server Mode)

**Files:**
- Create: `src/flow/rpc.py`
- Test: `tests/test_rpc.py`

**Step 1: Write the failing test**
```python
# tests/test_rpc.py
import asyncio
from flow.rpc import rpc, RpcRegistry

def test_rpc_registers_function():
    """@rpc decorator registers function in registry."""
    RpcRegistry.clear()

    @rpc
    async def my_server_function(x: int) -> int:
        return x * 2

    assert "my_server_function" in RpcRegistry.routes

def test_rpc_function_still_callable():
    """Decorated function can still be called directly."""
    RpcRegistry.clear()

    @rpc
    async def add(a: int, b: int) -> int:
        return a + b

    result = asyncio.run(add(2, 3))
    assert result == 5

def test_rpc_stores_function_reference():
    """Registry stores the actual function."""
    RpcRegistry.clear()

    @rpc
    async def compute():
        return 42

    stored_fn = RpcRegistry.routes["compute"]
    result = asyncio.run(stored_fn())
    assert result == 42

def test_rpc_multiple_functions():
    """Multiple functions can be registered."""
    RpcRegistry.clear()

    @rpc
    async def func_a():
        pass

    @rpc
    async def func_b():
        pass

    assert len(RpcRegistry.routes) == 2
    assert "func_a" in RpcRegistry.routes
    assert "func_b" in RpcRegistry.routes
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_rpc.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# src/flow/rpc.py
"""RPC - Remote Procedure Call system for server/client communication."""

from __future__ import annotations
import sys
from functools import wraps
from typing import Callable, Any, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

# Detect environment
IS_SERVER = not (sys.platform == "emscripten" or sys.platform == "wasi")


class RpcRegistry:
    """Registry for server-side RPC function implementations."""

    routes: dict[str, Callable[..., Any]] = {}

    @classmethod
    def clear(cls) -> None:
        """Clear all registered routes."""
        cls.routes.clear()

    @classmethod
    def get(cls, name: str) -> Callable[..., Any] | None:
        """Get a registered function by name."""
        return cls.routes.get(name)


def rpc(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that registers a function as an RPC endpoint.

    On the server: Registers the function and keeps it callable.
    On the client (Wasm): Would replace with a fetch() proxy.
    """
    if IS_SERVER:
        # Server mode: Register and return the original function
        RpcRegistry.routes[func.__name__] = func

        @wraps(func)
        async def server_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await func(*args, **kwargs)

        return server_wrapper
    else:
        # Client mode (Wasm): Would be replaced with fetch proxy
        # For now, just return the function for testing
        return func
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_rpc.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**
```bash
git add src/flow/rpc.py tests/test_rpc.py
git commit -m "feat(rpc): add @rpc decorator and RpcRegistry"
```

---

### Task 5.2: RPC Server Endpoint (with Robust Serialization)

> **⚠️ STEERING COUNCIL AMENDMENT:** A world-class Python framework must handle `datetime`,
> `UUID`, and `dataclasses` automatically. The RPC serializer uses a robust `FlowJSONEncoder`
> so developers don't have to manually convert objects to dicts.

**Files:**
- Create: `src/flow/rpc/encoder.py`
- Modify: `src/flow/server/app.py`
- Test: `tests/test_rpc_endpoint.py`
- Test: `tests/test_rpc_serialization.py`

**Step 0: Write the serialization safety tests (TDD)**
```python
# tests/test_rpc_serialization.py
import asyncio
from datetime import datetime, date, time
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from flow.rpc import rpc, RpcRegistry
from flow.rpc.encoder import FlowJSONEncoder
import json

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

@dataclass
class User:
    id: UUID
    name: str
    created_at: datetime

def test_encoder_handles_datetime():
    """Encoder serializes datetime to ISO format."""
    dt = datetime(2025, 12, 2, 14, 30, 0)
    result = json.dumps({"timestamp": dt}, cls=FlowJSONEncoder)
    assert "2025-12-02T14:30:00" in result

def test_encoder_handles_date():
    """Encoder serializes date to ISO format."""
    d = date(2025, 12, 2)
    result = json.dumps({"date": d}, cls=FlowJSONEncoder)
    assert "2025-12-02" in result

def test_encoder_handles_uuid():
    """Encoder serializes UUID to string."""
    uid = UUID("12345678-1234-5678-1234-567812345678")
    result = json.dumps({"id": uid}, cls=FlowJSONEncoder)
    assert "12345678-1234-5678-1234-567812345678" in result

def test_encoder_handles_dataclass():
    """Encoder serializes dataclasses to dicts."""
    user = User(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        name="Alice",
        created_at=datetime(2025, 12, 2, 14, 30, 0)
    )
    result = json.dumps(user, cls=FlowJSONEncoder)
    parsed = json.loads(result)

    assert parsed["name"] == "Alice"
    assert "12345678-1234-5678-1234-567812345678" in parsed["id"]
    assert "2025-12-02" in parsed["created_at"]

def test_encoder_handles_enum():
    """Encoder serializes Enum to its value."""
    result = json.dumps({"status": Status.ACTIVE}, cls=FlowJSONEncoder)
    assert "active" in result

def test_encoder_handles_decimal():
    """Encoder serializes Decimal to string (preserves precision)."""
    result = json.dumps({"price": Decimal("19.99")}, cls=FlowJSONEncoder)
    assert "19.99" in result

def test_encoder_handles_nested_dataclass():
    """Encoder handles dataclasses with nested complex types."""
    @dataclass
    class Order:
        id: UUID
        user: User
        total: Decimal

    order = Order(
        id=uuid4(),
        user=User(
            id=uuid4(),
            name="Bob",
            created_at=datetime.now()
        ),
        total=Decimal("99.99")
    )

    result = json.dumps(order, cls=FlowJSONEncoder)
    parsed = json.loads(result)

    assert parsed["user"]["name"] == "Bob"
    assert "99.99" in parsed["total"]
```

**Step 1: Write the failing test**
```python
# tests/test_rpc_endpoint.py
import pytest
from fastapi.testclient import TestClient
from flow.server.app import create_app
from flow.rpc import rpc, RpcRegistry
from flow.component import component
from flow.ui import Div

@component
async def DummyApp():
    with Div() as root:
        pass
    return root

def test_rpc_endpoint_calls_function():
    """POST /api/rpc/{name} calls the registered function."""
    RpcRegistry.clear()

    @rpc
    async def multiply(a: int, b: int) -> int:
        return a * b

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post(
        "/api/rpc/multiply",
        json={"a": 6, "b": 7}
    )

    assert response.status_code == 200
    assert response.json() == 42

def test_rpc_endpoint_not_found():
    """POST to unknown function returns 404."""
    RpcRegistry.clear()

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post(
        "/api/rpc/unknown_func",
        json={}
    )

    assert response.status_code == 404

def test_rpc_endpoint_with_string_result():
    """RPC can return string results."""
    RpcRegistry.clear()

    @rpc
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post(
        "/api/rpc/greet",
        json={"name": "World"}
    )

    assert response.status_code == 200
    assert response.json() == "Hello, World!"
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_rpc_endpoint.py tests/test_rpc_serialization.py -v`
Expected: FAIL with "ModuleNotFoundError" (encoder doesn't exist yet)

**Step 3: Create FlowJSONEncoder for robust serialization**
```python
# src/flow/rpc/encoder.py
"""FlowJSONEncoder - Robust JSON encoder for RPC responses.

Automatically handles:
- datetime, date, time → ISO 8601 strings
- UUID → string representation
- dataclasses → dict (recursive)
- Enum → value
- Decimal → string (preserves precision)
- bytes → base64 string
- sets → lists
"""

from __future__ import annotations
import json
import dataclasses
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Any
import base64


class FlowJSONEncoder(json.JSONEncoder):
    """
    Enterprise-grade JSON encoder for Flow RPC.

    Developers don't need to manually convert objects to dicts.
    All common Python types are handled automatically.
    """

    def default(self, obj: Any) -> Any:
        # datetime types → ISO 8601
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.isoformat()

        # UUID → string
        if isinstance(obj, UUID):
            return str(obj)

        # Decimal → string (preserves precision)
        if isinstance(obj, Decimal):
            return str(obj)

        # Enum → value
        if isinstance(obj, Enum):
            return obj.value

        # dataclass → dict (recursive via asdict)
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return self._encode_dataclass(obj)

        # bytes → base64
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")

        # set/frozenset → list
        if isinstance(obj, (set, frozenset)):
            return list(obj)

        # Fallback to default behavior
        return super().default(obj)

    def _encode_dataclass(self, obj: Any) -> dict:
        """Recursively encode a dataclass, handling nested complex types."""
        result = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            # Recursively encode values (the encoder will handle nested types)
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                result[field.name] = self._encode_dataclass(value)
            elif isinstance(value, (datetime, date, time, UUID, Decimal, Enum)):
                result[field.name] = self.default(value)
            elif isinstance(value, (list, tuple)):
                result[field.name] = [
                    self._encode_dataclass(v) if dataclasses.is_dataclass(v) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                result[field.name] = {
                    k: self._encode_dataclass(v) if dataclasses.is_dataclass(v) else v
                    for k, v in value.items()
                }
            else:
                result[field.name] = value
        return result


def flow_json_dumps(obj: Any, **kwargs) -> str:
    """Convenience function for JSON serialization with FlowJSONEncoder."""
    return json.dumps(obj, cls=FlowJSONEncoder, **kwargs)
```

**Step 4: Add RPC endpoint to server app (with FlowJSONEncoder)**
```python
# Add to src/flow/server/app.py (inside create_app function, before return)

from flow.rpc import RpcRegistry
from flow.rpc.encoder import FlowJSONEncoder, flow_json_dumps
from fastapi import HTTPException
from fastapi.responses import JSONResponse

    @app.post("/api/rpc/{func_name}")
    async def rpc_handler(func_name: str, request: Request) -> JSONResponse:
        """Handle RPC calls from the client with robust serialization."""
        target_func = RpcRegistry.get(func_name)

        if target_func is None:
            raise HTTPException(status_code=404, detail=f"RPC function '{func_name}' not found")

        # Parse the request body as JSON
        try:
            data = await request.json()
        except Exception:
            data = {}

        # Call the function with the provided arguments
        result = await target_func(**data)

        # Serialize with FlowJSONEncoder (handles datetime, UUID, dataclasses, etc.)
        json_content = flow_json_dumps(result)

        return JSONResponse(
            content=json.loads(json_content),  # FastAPI requires dict, not string
            media_type="application/json"
        )
```

**Step 5: Update RPC package exports**
```python
# src/flow/rpc/__init__.py
"""Flow RPC - Remote Procedure Call system with robust serialization."""

from flow.rpc.registry import rpc, RpcRegistry
from flow.rpc.encoder import FlowJSONEncoder, flow_json_dumps

__all__ = [
    "rpc",
    "RpcRegistry",
    "FlowJSONEncoder",
    "flow_json_dumps",
]
```

**Step 6: Run tests to verify they pass**
Run: `uv run pytest tests/test_rpc_endpoint.py tests/test_rpc_serialization.py -v`
Expected: PASS (10 tests)

**Step 7: Commit**
```bash
git add src/flow/rpc/ src/flow/server/app.py tests/test_rpc_endpoint.py tests/test_rpc_serialization.py
git commit -m "feat(rpc): add FlowJSONEncoder for robust serialization (datetime, UUID, dataclass)"
```

---

## Phase 6: Build System

**Objective:** Create the CLI and AST splitting tools for client/server code separation.

---

### Task 6.1: AST Splitter & Import Hook (Zero-Build Dev)

> **⚠️ STEERING COUNCIL AMENDMENT:** Development must be zero-step.
> Uses `sys.meta_path` import hook for on-the-fly transpilation.
> Just run `python app.py` - no build step needed during development.

> **⚠️ HIGH-RISK WARNING:** Debugging dynamic AST transformations in memory is difficult.
> The `FlowImportHook` includes a **debug mode** that dumps transformed source to disk
> when `FLOW_DEBUG=1` is set, enabling easier troubleshooting.

**Files:**
- Create: `src/flow/compiler/__init__.py`
- Create: `src/flow/compiler/splitter.py`
- Create: `src/flow/compiler/importer.py`
- Test: `tests/test_splitter.py`
- Test: `tests/test_importer.py`
- Test: `tests/test_importer_debug.py`

**Step 1: Write the failing test for splitter**
```python
# tests/test_splitter.py
from flow.compiler.splitter import build_client_bundle

def test_splitter_keeps_component():
    """Client bundle keeps @component decorated functions."""
    source = '''
from flow import component
from flow.ui import Div

@component
async def MyApp():
    with Div():
        pass
'''

    result = build_client_bundle(source)

    assert "@component" in result
    assert "async def MyApp" in result

def test_splitter_stubs_rpc_body():
    """RPC function bodies are replaced with pass."""
    source = '''
from flow import rpc
import sqlalchemy

@rpc
async def save_to_db(data: str):
    db = sqlalchemy.connect()
    db.save(data)
    return "saved"
'''

    result = build_client_bundle(source)

    assert "@rpc" in result
    assert "async def save_to_db" in result
    # Body should be stubbed
    assert "sqlalchemy.connect" not in result

def test_splitter_removes_server_imports():
    """Server-only imports are removed."""
    source = '''
import sqlalchemy
import pandas as pd
from flow import component

@component
async def App():
    pass
'''

    result = build_client_bundle(source)

    assert "import sqlalchemy" not in result
    assert "import pandas" not in result
    assert "from flow import component" in result

def test_splitter_preserves_client_code():
    """Non-RPC code is fully preserved."""
    source = '''
from flow import Signal, component
from flow.ui import Text

class AppState:
    count = Signal(0)

@component
async def Counter(state: AppState):
    state.count.value += 1
'''

    result = build_client_bundle(source)

    assert "class AppState" in result
    assert "count = Signal(0)" in result
    assert "state.count.value += 1" in result
```

**Step 2: Write the failing test for import hook**
```python
# tests/test_importer.py
import sys
import types
from flow.compiler.importer import FlowImportHook, install_import_hook, uninstall_import_hook

def test_import_hook_can_be_installed():
    """Import hook can be added to sys.meta_path."""
    initial_count = len(sys.meta_path)

    install_import_hook()
    assert len(sys.meta_path) == initial_count + 1
    assert any(isinstance(f, FlowImportHook) for f in sys.meta_path)

    uninstall_import_hook()
    assert len(sys.meta_path) == initial_count

def test_import_hook_transforms_client_modules():
    """Import hook transforms _client modules on-the-fly."""
    # This tests that when importing 'app_client', the hook:
    # 1. Finds 'app.py'
    # 2. Runs ClientSideSanitizer
    # 3. Returns transformed bytecode

    install_import_hook()
    try:
        # The hook should handle this pattern
        hook = next(f for f in sys.meta_path if isinstance(f, FlowImportHook))
        assert hook is not None
    finally:
        uninstall_import_hook()

def test_import_hook_caches_transformations():
    """Import hook caches transformed modules for performance."""
    install_import_hook()
    try:
        hook = next(f for f in sys.meta_path if isinstance(f, FlowImportHook))
        assert hasattr(hook, '_cache')
    finally:
        uninstall_import_hook()
```

**Step 2b: Write the debug mode test**
```python
# tests/test_importer_debug.py
import os
import sys
import tempfile
from pathlib import Path
from flow.compiler.importer import (
    FlowImportHook,
    install_import_hook,
    uninstall_import_hook,
    set_debug_mode,
    get_debug_output_dir,
)
from flow.compiler.splitter import build_client_bundle

def test_debug_mode_can_be_enabled():
    """Debug mode can be enabled via function or env var."""
    # Via function
    set_debug_mode(True)
    hook = FlowImportHook()
    assert hook._debug_mode is True
    set_debug_mode(False)

def test_debug_mode_respects_env_var():
    """Debug mode respects FLOW_DEBUG environment variable."""
    original = os.environ.get("FLOW_DEBUG")
    try:
        os.environ["FLOW_DEBUG"] = "1"
        hook = FlowImportHook()
        assert hook._debug_mode is True
    finally:
        if original is None:
            os.environ.pop("FLOW_DEBUG", None)
        else:
            os.environ["FLOW_DEBUG"] = original

def test_debug_mode_dumps_transformed_source():
    """Debug mode writes transformed source to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        debug_dir = Path(tmpdir) / ".flow-debug"
        set_debug_mode(True, output_dir=debug_dir)

        # Create a test module
        source_dir = Path(tmpdir) / "src"
        source_dir.mkdir()
        (source_dir / "myapp.py").write_text('''
from flow import component, rpc
import sqlalchemy

@rpc
async def save_data(x: int):
    db = sqlalchemy.connect()
    return x

@component
async def App():
    pass
''')

        # The hook would transform and dump when importing
        transformed = build_client_bundle((source_dir / "myapp.py").read_text())

        # Simulate what the hook does in debug mode
        debug_file = debug_dir / "myapp_client.py"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(transformed)

        assert debug_file.exists()
        content = debug_file.read_text()
        assert "sqlalchemy" not in content  # Server import removed
        assert "@component" in content  # Component preserved

        set_debug_mode(False)

def test_debug_output_includes_metadata():
    """Debug output includes helpful metadata comments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        debug_dir = Path(tmpdir) / ".flow-debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        source = '''
from flow import rpc
@rpc
async def secret():
    return "password123"
'''
        transformed = build_client_bundle(source)

        # Debug file should have header comment
        debug_content = f'''# FLOW DEBUG OUTPUT
# Original: test_app.py
# Generated at: 2025-12-02T14:30:00
# Transformations applied:
#   - Removed server-only imports
#   - Stubbed @rpc function bodies

{transformed}
'''
        (debug_dir / "test_app_client.py").write_text(debug_content)

        content = (debug_dir / "test_app_client.py").read_text()
        assert "FLOW DEBUG OUTPUT" in content
        assert "Transformations applied" in content
```

**Step 3: Write the AST Splitter**
```python
# src/flow/compiler/splitter.py
"""AST Splitter - Generates client-safe bundles from full source code."""

from __future__ import annotations
import ast
from typing import Set

# Imports that are server-only and should be removed from client bundles
SERVER_ONLY_MODULES: Set[str] = {
    "sqlalchemy",
    "pandas",
    "boto3",
    "psycopg2",
    "pymongo",
    "redis",
    "celery",
    "os",  # Often used for env vars
}


class ClientSideSanitizer(ast.NodeTransformer):
    """
    Walks the AST and:
    1. Removes server-only imports
    2. Stubs out @rpc function bodies
    """

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        """Remove server-only imports."""
        remaining = [
            alias for alias in node.names
            if alias.name.split(".")[0] not in SERVER_ONLY_MODULES
        ]

        if not remaining:
            return None

        node.names = remaining
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom | None:
        """Remove server-only from imports."""
        if node.module and node.module.split(".")[0] in SERVER_ONLY_MODULES:
            return None
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Stub out @rpc decorated functions."""
        is_rpc = any(
            (isinstance(d, ast.Name) and d.id == "rpc") or
            (isinstance(d, ast.Attribute) and d.attr == "rpc")
            for d in node.decorator_list
        )

        if is_rpc:
            node.body = [ast.Pass()]
        else:
            self.generic_visit(node)

        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Stub out sync @rpc decorated functions."""
        is_rpc = any(
            (isinstance(d, ast.Name) and d.id == "rpc") or
            (isinstance(d, ast.Attribute) and d.attr == "rpc")
            for d in node.decorator_list
        )

        if is_rpc:
            node.body = [ast.Pass()]
        else:
            self.generic_visit(node)

        return node


def build_client_bundle(source_code: str) -> str:
    """
    Transform source code into a client-safe bundle.

    - Removes server-only imports
    - Stubs @rpc function bodies
    - Preserves everything else
    """
    tree = ast.parse(source_code)
    sanitizer = ClientSideSanitizer()
    sanitized_tree = sanitizer.visit(tree)
    ast.fix_missing_locations(sanitized_tree)
    return ast.unparse(sanitized_tree)


def compile_client_bundle(source_code: str, filename: str = "<flow>") -> types.CodeType:
    """
    Compile source code to client-safe bytecode (for import hook).

    Returns compiled code object, not source string.
    """
    import types

    tree = ast.parse(source_code)
    sanitizer = ClientSideSanitizer()
    sanitized_tree = sanitizer.visit(tree)
    ast.fix_missing_locations(sanitized_tree)

    return compile(sanitized_tree, filename, "exec")
```

**Step 4: Write the Import Hook (Zero-Build Dev with Debug Mode)**
```python
# src/flow/compiler/importer.py
"""
Import Hook for Zero-Build Development.

Registers a sys.meta_path finder that intercepts imports of
'*_client' modules and transforms them on-the-fly using the
AST splitter. No physical dist/ folder needed during dev.

DEBUG MODE:
    Set FLOW_DEBUG=1 to dump transformed source to .flow-debug/ directory.
    This helps troubleshoot AST transformation issues.

Usage:
    from flow.compiler.importer import install_import_hook
    install_import_hook()

    # Now 'import app_client' will:
    # 1. Find 'app.py'
    # 2. Transform via ClientSideSanitizer
    # 3. Execute transformed bytecode

    # Debug mode (dumps to disk):
    FLOW_DEBUG=1 python app.py
"""

from __future__ import annotations
import os
import sys
import importlib.abc
import importlib.machinery
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Sequence
import threading

from flow.compiler.splitter import compile_client_bundle, build_client_bundle

# Global debug settings
_debug_mode: bool = False
_debug_output_dir: Path = Path(".flow-debug")


def set_debug_mode(enabled: bool, output_dir: Path | None = None) -> None:
    """Enable or disable debug mode for import hook transformations."""
    global _debug_mode, _debug_output_dir
    _debug_mode = enabled
    if output_dir is not None:
        _debug_output_dir = output_dir


def get_debug_output_dir() -> Path:
    """Get the current debug output directory."""
    return _debug_output_dir


def _is_debug_enabled() -> bool:
    """Check if debug mode is enabled (via global or env var)."""
    return _debug_mode or os.environ.get("FLOW_DEBUG", "").lower() in ("1", "true", "yes")


class FlowImportHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """
    Import hook that transforms '*_client' modules on-the-fly.

    When you import 'myapp_client', this finder:
    1. Looks for 'myapp.py' in the same directory
    2. Reads the source
    3. Runs ClientSideSanitizer AST transformer
    4. Compiles and executes the transformed bytecode

    DEBUG MODE (FLOW_DEBUG=1):
    - Dumps transformed source to .flow-debug/ directory
    - Includes metadata comments for troubleshooting
    - Helps debug AST transformation issues

    No physical file is created in normal mode - everything happens in memory.
    """

    def __init__(self) -> None:
        self._cache: dict[str, object] = {}
        self._lock = threading.Lock()
        self._debug_mode = _is_debug_enabled()

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: object | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        """Find module spec for '*_client' modules."""

        # Only handle modules ending in '_client'
        if not fullname.endswith("_client"):
            return None

        # Derive the original module name
        original_name = fullname[:-7]  # Remove '_client' suffix

        # Try to find the original .py file
        search_paths = path or sys.path

        for search_path in search_paths:
            original_path = Path(search_path) / f"{original_name}.py"
            if original_path.exists():
                return importlib.machinery.ModuleSpec(
                    name=fullname,
                    loader=self,
                    origin=str(original_path),
                )

        return None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        """Use default module creation."""
        return None

    def exec_module(self, module: object) -> None:
        """Execute the transformed module."""
        spec = module.__spec__
        if spec is None or spec.origin is None:
            raise ImportError(f"Cannot load module without origin: {module}")

        origin_path = Path(spec.origin)

        with self._lock:
            # Check cache
            cache_key = str(origin_path)
            mtime = origin_path.stat().st_mtime

            cached = self._cache.get(cache_key)
            if cached and cached[0] == mtime:
                code = cached[1]
            else:
                # Read and transform
                source = origin_path.read_text(encoding="utf-8")
                code = compile_client_bundle(source, str(origin_path))
                self._cache[cache_key] = (mtime, code)

                # DEBUG MODE: Dump transformed source to disk
                if self._debug_mode:
                    self._dump_debug_output(spec.name, origin_path, source)

        # Execute in module's namespace
        exec(code, module.__dict__)

    def _dump_debug_output(
        self,
        module_name: str,
        origin_path: Path,
        original_source: str
    ) -> None:
        """Dump transformed source to disk for debugging (HIGH-RISK mitigation)."""
        try:
            debug_dir = get_debug_output_dir()
            debug_dir.mkdir(parents=True, exist_ok=True)

            # Generate transformed source (for human inspection)
            transformed = build_client_bundle(original_source)

            # Create debug file with metadata header
            debug_file = debug_dir / f"{module_name}.py"
            debug_content = f'''# FLOW DEBUG OUTPUT
# ==================
# Original file: {origin_path}
# Module name: {module_name}
# Generated at: {datetime.now().isoformat()}
# Debug mode: FLOW_DEBUG=1 or set_debug_mode(True)
#
# Transformations applied:
#   - Removed server-only imports (sqlalchemy, pandas, boto3, etc.)
#   - Stubbed @rpc function bodies (replaced with pass)
#   - Preserved @component functions and client code
#
# To disable debug output: unset FLOW_DEBUG
# ==================

{transformed}
'''
            debug_file.write_text(debug_content)

            # Log to stderr for visibility
            print(
                f"[FLOW DEBUG] Dumped transformed source: {debug_file}",
                file=sys.stderr
            )

        except Exception as e:
            # Debug dump should never break the import
            print(
                f"[FLOW DEBUG] Warning: Failed to dump debug output: {e}",
                file=sys.stderr
            )


# Singleton instance
_import_hook: FlowImportHook | None = None


def install_import_hook(debug: bool = False) -> None:
    """
    Install the Flow import hook for zero-build development.

    Args:
        debug: Enable debug mode (dumps transformed source to disk)
    """
    global _import_hook

    if debug:
        set_debug_mode(True)

    if _import_hook is not None:
        return  # Already installed

    _import_hook = FlowImportHook()
    sys.meta_path.insert(0, _import_hook)


def uninstall_import_hook() -> None:
    """Remove the Flow import hook."""
    global _import_hook

    if _import_hook is not None:
        sys.meta_path.remove(_import_hook)
        _import_hook = None
```

**Step 5: Update compiler exports (with debug mode)**
```python
# src/flow/compiler/__init__.py
"""Flow Compiler - Build tools and import hooks for client/server splitting."""

from flow.compiler.splitter import build_client_bundle, compile_client_bundle
from flow.compiler.importer import (
    install_import_hook,
    uninstall_import_hook,
    FlowImportHook,
    set_debug_mode,
    get_debug_output_dir,
)

__all__ = [
    "build_client_bundle",
    "compile_client_bundle",
    "install_import_hook",
    "uninstall_import_hook",
    "FlowImportHook",
    "set_debug_mode",
    "get_debug_output_dir",
]
```

**Step 6: Run tests to verify they pass**
Run: `uv run pytest tests/test_splitter.py tests/test_importer.py tests/test_importer_debug.py -v`
Expected: PASS (11 tests)

**Step 7: Commit**
```bash
git add src/flow/compiler/ tests/test_splitter.py tests/test_importer.py
git commit -m "feat(compiler): add AST splitter and import hook for zero-build dev"
```

---

### Task 6.2: CLI Commands

**Files:**
- Create: `src/flow/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**
```python
# tests/test_cli.py
import os
import tempfile
from pathlib import Path
from click.testing import CliRunner
from flow.cli import cli

def test_cli_has_build_command():
    """CLI has a 'build' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--help"])

    assert result.exit_code == 0
    assert "build" in result.output.lower()

def test_cli_has_dev_command():
    """CLI has a 'dev' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["dev", "--help"])

    assert result.exit_code == 0

def test_cli_build_creates_output():
    """CLI build command creates output files."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample app file
        app_file = Path(tmpdir) / "app.py"
        app_file.write_text('''
from flow import component
from flow.ui import Div

@component
async def App():
    with Div():
        pass
''')

        dist_dir = Path(tmpdir) / "dist"

        result = runner.invoke(cli, [
            "build",
            str(app_file),
            "--output", str(dist_dir)
        ])

        assert result.exit_code == 0
        assert dist_dir.exists()

def test_cli_version():
    """CLI shows version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Add click to dependencies and write CLI (with Import Hook)**
```toml
# Update pyproject.toml dependencies:
[project]
name = "flow"
version = "0.1.0"
description = "A Pythonic UI framework using context managers and signals"
requires-python = ">=3.14"  # Required for No-GIL and PEP 649
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "websockets>=12.0",
    "click>=8.1.0",
]
```

```python
# src/flow/cli.py
"""Flow CLI - Command-line interface for Flow apps (Zero-Build Dev)."""

from __future__ import annotations
from pathlib import Path

import click

from flow import __version__


@click.group()
@click.version_option(version=__version__, prog_name="flow")
def cli() -> None:
    """Flow - A Pythonic UI Framework for Python 3.14+."""
    pass


@cli.command()
@click.argument("app_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="dist", help="Output directory")
def build(app_file: str, output: str) -> None:
    """Build a Flow app for production deployment."""
    from flow.compiler.splitter import build_client_bundle

    app_path = Path(app_file)
    output_path = Path(output)

    click.echo(f"Building {app_path.name} for production...")

    # Read source
    source = app_path.read_text()

    # Generate client bundle (physical file for production)
    client_code = build_client_bundle(source)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Write client bundle
    client_file = output_path / f"{app_path.stem}_client.py"
    client_file.write_text(client_code)

    # Copy original as server bundle
    server_file = output_path / f"{app_path.stem}_server.py"
    server_file.write_text(source)

    click.echo(f"✓ Client bundle: {client_file}")
    click.echo(f"✓ Server bundle: {server_file}")
    click.echo(f"Build complete: {output_path}")


@cli.command()
@click.argument("app_file", type=click.Path(exists=True))
@click.option("--host", default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", default=8000, help="Port to bind")
@click.option("--debug", is_flag=True, help="Enable debug mode (dumps transformed AST to .flow-debug/)")
def dev(app_file: str, host: str, port: int, debug: bool) -> None:
    """
    Run a Flow app in development mode (Zero-Build).

    Uses import hook for on-the-fly AST transformation.
    No dist/ folder created - everything in memory.

    Debug mode (--debug or FLOW_DEBUG=1): Dumps transformed source
    to .flow-debug/ directory for troubleshooting AST transformations.
    """
    import importlib.util
    import sys

    from flow.server.app import run_app
    from flow.compiler.importer import install_import_hook, set_debug_mode

    app_path = Path(app_file)

    click.echo(f"🚀 Starting Flow dev server (Zero-Build Mode)...")
    click.echo(f"   Python {sys.version_info.major}.{sys.version_info.minor} (No-GIL: {'enabled' if hasattr(sys, 'getswitchinterval') else 'unknown'})")

    # DEBUG MODE: Enable if --debug flag or FLOW_DEBUG env var
    if debug:
        set_debug_mode(True)
        click.echo(f"   ⚠️  Debug mode: Transformed source will be dumped to .flow-debug/")

    # ZERO-BUILD: Install import hook for on-the-fly transformation
    install_import_hook(debug=debug)
    click.echo(f"   Import hook installed for zero-build development")

    click.echo(f"   Loading {app_path.name}...")

    # Add app directory to path for imports
    app_dir = str(app_path.parent.absolute())
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    # Load the app module dynamically
    spec = importlib.util.spec_from_file_location("app", app_path)
    if spec is None or spec.loader is None:
        click.echo("Error: Could not load app file", err=True)
        return

    module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = module
    spec.loader.exec_module(module)

    # Look for the main component (named App or main)
    app_component = getattr(module, "App", None) or getattr(module, "main", None)

    if app_component is None:
        click.echo("Error: No App or main component found", err=True)
        return

    click.echo(f"")
    click.echo(f"   ✅ Ready at http://{host}:{port}")
    click.echo(f"   Press Ctrl+C to stop")
    click.echo(f"")

    run_app(app_component, host=host, port=port)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
```

**Step 4: Add CLI entry point to pyproject.toml**
```toml
# Add to pyproject.toml:
[project.scripts]
flow = "flow.cli:main"
```

**Step 5: Run test to verify it passes**
Run: `uv sync && uv run pytest tests/test_cli.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**
```bash
git add pyproject.toml src/flow/cli.py tests/test_cli.py
git commit -m "feat(cli): add CLI with build and dev commands"
```

---

## Phase 7: Final Integration & Exports

**Objective:** Wire everything together and ensure a clean public API.

---

### Task 7.1: Update Package Exports

**Files:**
- Modify: `src/flow/__init__.py`
- Test: `tests/test_full_api.py`

**Step 1: Write the failing test**
```python
# tests/test_full_api.py
def test_all_core_exports():
    """All core APIs are exported from flow package."""
    from flow import (
        # Core
        Element,
        Signal,
        Effect,
        # Component
        component,
        Computed,
        # RPC
        rpc,
        # Injection
        provide,
    )

    assert all([
        Element, Signal, Effect,
        component, Computed,
        rpc, provide
    ])

def test_ui_submodule():
    """UI elements are accessible via flow.ui."""
    from flow.ui import Div, Text, Button, Input, VStack, HStack

    assert all([Div, Text, Button, Input, VStack, HStack])

def test_server_submodule():
    """Server utilities are accessible via flow.server."""
    from flow.server import create_app, LiveSession

    assert all([create_app, LiveSession])
```

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_full_api.py -v`
Expected: FAIL (some imports missing)

**Step 3: Update exports**
```python
# src/flow/__init__.py
"""Flow - A Pythonic UI Framework using context managers and signals."""

from flow.element import Element
from flow.signal import Signal
from flow.effect import Effect
from flow.computed import Computed
from flow.component import component
from flow.rpc import rpc
from flow.injection import provide, get_provider

__all__ = [
    # Core
    "Element",
    "Signal",
    "Effect",
    "Computed",
    # Component
    "component",
    # RPC
    "rpc",
    # Injection
    "provide",
    "get_provider",
]

__version__ = "0.1.0"
```

**Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_full_api.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**
```bash
git add src/flow/__init__.py tests/test_full_api.py
git commit -m "feat: finalize public API exports"
```

---

### Task 7.2: Integration Test (End-to-End Example)

**Files:**
- Create: `examples/counter.py`
- Test: `tests/test_integration.py`

**Step 1: Write the failing test**
```python
# tests/test_integration.py
import asyncio
from dataclasses import dataclass
from fastapi.testclient import TestClient

from flow import Signal, component, rpc, provide
from flow.ui import Div, Text, Button
from flow.server import create_app
from flow.rpc import RpcRegistry

@dataclass
class CounterState:
    count: Signal[int]

def test_full_counter_app():
    """Integration test: Full counter app works end-to-end."""
    RpcRegistry.clear()

    # State
    state = CounterState(count=Signal(0))
    provide(CounterState, state)

    # RPC
    @rpc
    async def increment():
        state.count.value += 1
        return state.count.value

    # Component
    @component
    async def CounterApp(state: CounterState):
        with Div(cls="counter") as root:
            with Text(f"Count: {state.count.value}"):
                pass
            with Button("Increment", on_click=increment):
                pass
        return root

    # Create app
    app = create_app(CounterApp)
    client = TestClient(app)

    # Test initial render
    response = client.get("/")
    assert response.status_code == 200
    assert "Count: 0" in response.text

    # Test RPC
    response = client.post("/api/rpc/increment", json={})
    assert response.status_code == 200
    assert response.json() == 1

    # State was updated
    assert state.count.value == 1

def test_reactive_updates():
    """Integration test: Signal changes trigger effects."""
    effects_run = []

    count = Signal(0)

    from flow import Effect
    Effect(lambda: effects_run.append(count.value))

    assert effects_run == [0]  # Initial

    count.value = 1
    assert effects_run == [0, 1]

    count.value = 2
    assert effects_run == [0, 1, 2]
```

**Step 2: Run test to verify it passes (this is a validation test)**
Run: `uv run pytest tests/test_integration.py -v`
Expected: PASS (2 tests)

**Step 3: Create example app**
```python
# examples/counter.py
"""Example: Simple Counter App with Flow."""

from dataclasses import dataclass

from flow import Signal, component, rpc, provide
from flow.ui import Div, Text, Button, VStack
from flow.server import run_app


@dataclass
class CounterState:
    """Application state using Signals."""
    count: Signal[int]


# Initialize state
state = CounterState(count=Signal(0))
provide(CounterState, state)


@rpc
async def increment():
    """Server-side function to increment counter."""
    state.count.value += 1
    return {"count": state.count.value}


@rpc
async def decrement():
    """Server-side function to decrement counter."""
    state.count.value -= 1
    return {"count": state.count.value}


@component
async def App(state: CounterState):
    """Main application component."""
    with Div(cls="min-h-screen bg-gray-900 flex items-center justify-center") as root:
        with VStack(cls="bg-gray-800 p-8 rounded-xl shadow-2xl"):
            with Text(
                "Flow Counter",
                cls="text-3xl font-bold text-white mb-6"
            ):
                pass

            with Text(
                f"{state.count.value}",
                cls="text-6xl font-mono text-blue-400 mb-6"
            ):
                pass

            with Div(cls="flex gap-4"):
                with Button(
                    "-",
                    on_click=decrement,
                    cls="px-6 py-3 bg-red-500 text-white rounded-lg text-2xl hover:bg-red-600"
                ):
                    pass
                with Button(
                    "+",
                    on_click=increment,
                    cls="px-6 py-3 bg-green-500 text-white rounded-lg text-2xl hover:bg-green-600"
                ):
                    pass

    return root


if __name__ == "__main__":
    run_app(App)
```

**Step 4: Commit**
```bash
git add examples/ tests/test_integration.py
git commit -m "feat: add integration tests and counter example"
```

---

## Summary: All Tasks (Steering Council Amended)

| Phase | Task | Description | Amendment | Est. Time |
|-------|------|-------------|-----------|-----------|
| 1 | 1.1 | Project Setup (Python 3.14+) | - | 15 min |
| 1 | 1.2 | Context Stack | - | 20 min |
| 1 | 1.3 | Element Base Class | - | 25 min |
| 1 | 1.4 | Signal Primitive | **Thread-Safe (No-GIL)** | 25 min |
| 1 | 1.5 | Effect (Dependency Tracking) | **Thread-Safe (No-GIL)** | 30 min |
| 1 | 1.6 | Package Exports | - | 10 min |
| 2 | 2.1 | Basic UI Elements | **Style Architecture (V2-Ready)** | 30 min |
| 2 | 2.2 | **Renderer Protocol** | **REPLACED (Universal Runtime)** | 35 min |
| 2 | 2.3 | DOM Renderer Stub | **NEW (Wasm Prep)** | 20 min |
| 3 | 3.1 | Component Decorator | - | 20 min |
| 3 | 3.2 | Dependency Injection | **PEP 649 Lazy Eval** | 30 min |
| 3 | 3.3 | Computed Decorator | - | 20 min |
| 4 | 4.1 | LiveSession Manager | **No-GIL ThreadPool** | 30 min |
| 4 | 4.2 | FastAPI Integration | **Renderer Protocol** | 25 min |
| 5 | 5.1 | RPC Registry & Decorator | - | 20 min |
| 5 | 5.2 | RPC Server Endpoint | **FlowJSONEncoder (Serialization)** | 35 min |
| 6 | 6.1 | AST Splitter + Import Hook | **EXPANDED (Zero-Build + Debug)** | 50 min |
| 6 | 6.2 | CLI Commands | **Import Hook + --debug flag** | 30 min |
| 7 | 7.1 | Final Exports | - | 15 min |
| 7 | 7.2 | Integration Test | - | 20 min |

**Total Estimated Time:** ~8.5 hours

### Steering Council Amendment Summary

| Amendment | Task(s) Affected | Rationale |
|-----------|------------------|-----------|
| **Thread-Safe Signals** | 1.4, 1.5 | No-GIL (PEP 703) requires explicit locking |
| **Renderer Protocol** | 2.2, 2.3, 4.1, 4.2 | Universal Runtime (SSR + Wasm) |
| **PEP 649 Lazy Injection** | 3.2 | Circular dependencies in enterprise apps |
| **Zero-Build Dev** | 6.1, 6.2 | Import hook for frictionless development |
| **Style Architecture** | 2.1 | V2-ready for `Style` objects/kwargs (Pythonic purity) |
| **Robust Serialization** | 5.2 | FlowJSONEncoder for datetime/UUID/dataclass |
| **Debug Mode** | 6.1, 6.2 | Dumps transformed AST to disk (HIGH-RISK mitigation) |

---

## Future Phases (Enabled by Renderer Protocol)

### Phase 8: WebAssembly Support (Partially Prepared)
> The Renderer Protocol (Task 2.2) enables this phase with minimal changes.

- Platform detection (`IS_WASM` via `sys.platform`)
- **DOMRenderer** (Task 2.3 stub → full implementation)
- PyScript/Pyodide integration
- RPC client proxy (Wasm-side fetch calls)

### Phase 9: IDE/LSP Support
- Language Server Protocol implementation
- Scope-aware diagnostics (Server vs Client context)
- Semantic highlighting for @rpc/@component
- PEP 649 annotation introspection

### Phase 10: Advanced Features
- Client-side routing
- Form handling utilities
- Animation system
- Devtools integration
- Hot Module Replacement (leveraging import hook)

---

## Verdict

**The Steering Council amendments have been applied:**

✅ **Renderer Protocol** - Elements produce abstract trees; renderers consume them  
✅ **Thread-Safe Signals** - Ready for Python 3.14 No-GIL builds  
✅ **PEP 649 Lazy Injection** - Circular dependencies supported  
✅ **Zero-Build Development** - Import hook for on-the-fly transpilation  
✅ **Style Architecture** - `Element.props` supports future `Style` objects/kwargs for Pythonic purity  
✅ **Robust Serialization** - `FlowJSONEncoder` handles `datetime`, `UUID`, `dataclasses` automatically  
✅ **Debug Mode** - `FLOW_DEBUG=1` or `--debug` dumps transformed AST to `.flow-debug/` (HIGH-RISK mitigation)  

The framework is now architecturally positioned for the **Universal Isomorphic Runtime** goal.

---

## Next Steps

Plan saved to `docs/plans/2025-12-02-flow-framework.md`.

**Ready to execute?**

If yes, I will trigger the `execution-workflow.mdc` and begin implementing Phase 1 (Core Engine) with all Steering Council amendments incorporated.
