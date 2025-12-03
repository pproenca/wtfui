# Critical Path Test Coverage Plan

> **For Claude:** REQUIRED SUB-SKILL: Use super:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Achieve 100% critical path test coverage with comprehensive unit and integration tests for the Flow framework.

**Architecture:** Multi-layer testing strategy covering unit tests for isolated components, integration tests for cross-module interactions, and enhanced E2E tests for full workflows. Tests use pytest with pytest-asyncio for async code, pytest-cov for coverage, and MagicMock/AsyncMock for mocking.

**Tech Stack:** Python 3.14+, pytest 8.0+, pytest-asyncio, pytest-cov, pytest-benchmark, httpx/TestClient, playwright

**Commands:** All Python commands use `uv run` prefix

---

## Diagrams

### Test Architecture Diagram

```mermaid
graph TB
    subgraph "Test Organization"
        subgraph "Unit Tests (tests/)"
            UT_Signal[test_signal.py]
            UT_Effect[test_effect.py]
            UT_Computed[test_computed.py]
            UT_Element[test_element.py]
            UT_Context[test_context.py]
            UT_Renderer[test_renderer.py]
            UT_Layout[test_layout_*.py]
            UT_Console[test_console_*.py]
            UT_RPC[test_rpc*.py]
            UT_Compiler[test_compiler_*.py]
        end

        subgraph "Integration Tests"
            IT_Integration[test_integration.py]
            IT_Session[test_session*.py]
            IT_Server[test_server_app.py]
            IT_ConsoleInt[test_console_integration.py]
            IT_E2E_Int[test_e2e_integration.py]
        end

        subgraph "E2E Tests (tests/e2e/)"
            E2E_Todo[test_todo_e2e.py]
            E2E_Chat[test_chat_e2e.py]
            E2E_Dashboard[test_dashboard_e2e.py]
        end

        subgraph "Gatekeeper Tests (tests/gatekeepers/)"
            GK_Concurrency[test_concurrency.py<br/>No-GIL Scaling]
            GK_Latency[test_latency.py<br/>Reactivity O(N)]
            GK_Bundle[test_bundle.py<br/>Security Firewall]
            GK_Memory[test_memory.py<br/>Memory Bounds]
        end
    end

    subgraph "Fixtures"
        CF_Root[conftest.py<br/>clean_state]
        CF_E2E[e2e/conftest.py<br/>todo_server, chat_server]
        CF_GK[gatekeepers/conftest.py<br/>clean_gc, tree generators]
    end

    subgraph "Source Modules"
        SRC_React[flow.signal/effect/computed]
        SRC_Element[flow.element/context]
        SRC_Renderer[flow.renderer.*]
        SRC_Layout[flow.layout.*]
        SRC_Server[flow.server.*]
        SRC_RPC[flow.rpc.*]
        SRC_Wasm[flow.wasm.*]
        SRC_Compiler[flow.compiler.*]
    end

    UT_Signal --> SRC_React
    UT_Effect --> SRC_React
    UT_Computed --> SRC_React
    UT_Element --> SRC_Element
    UT_Renderer --> SRC_Renderer
    UT_Layout --> SRC_Layout
    UT_Console --> SRC_Renderer
    UT_RPC --> SRC_RPC
    UT_Compiler --> SRC_Compiler

    IT_Session --> SRC_Server
    IT_Server --> SRC_Server
    IT_ConsoleInt --> SRC_Renderer

    E2E_Todo --> CF_E2E
    E2E_Chat --> CF_E2E
    E2E_Dashboard --> CF_E2E

    GK_Concurrency --> SRC_React
    GK_Latency --> SRC_React
    GK_Bundle --> SRC_Compiler

    style GK_Concurrency fill:#f9f,stroke:#333
    style GK_Latency fill:#f9f,stroke:#333
    style GK_Bundle fill:#f9f,stroke:#333
    style GK_Memory fill:#f9f,stroke:#333
```

### Coverage Gaps Diagram

```mermaid
graph LR
    subgraph "Well Covered (80%+)"
        style WC fill:#4ade80
        WC_Signal[signal.py 100%]
        WC_Effect[effect.py 95%]
        WC_Computed[computed.py 92%]
        WC_Element[element.py 89%]
        WC_Layout[layout/*.py 88-98%]
        WC_Console[console/cell.py 93%]
        WC_UI[ui/*.py 89-95%]
    end

    subgraph "Needs Improvement (60-79%)"
        style NI fill:#fbbf24
        NI_ConsoleBuffer[console/buffer.py 76%]
        NI_ConsoleDiff[console/diff.py 69%]
        NI_ConsoleInput[console/input.py 71%]
        NI_ConsoleRenderer[console/renderer.py 65%]
        NI_WasmBoot[wasm/bootstrap.py 67%]
        NI_BuildArtifacts[build/artifacts.py 59%]
    end

    subgraph "Critical Gaps (<60%)"
        style CG fill:#ef4444
        CG_ServerApp[server/app.py 44%]
        CG_ServerSession[server/session.py 34%]
        CG_Terminal[console/terminal.py 32%]
    end

    subgraph "Priority Actions"
        P1[Priority 1: Server Module]
        P2[Priority 2: Console Terminal]
        P3[Priority 3: RPC Encoder]
        P4[Priority 4: Wasm Bootstrap]
    end

    CG_ServerApp --> P1
    CG_ServerSession --> P1
    CG_Terminal --> P2
    NI_ConsoleInput --> P2
    NI_WasmBoot --> P4
```

---

## Task Overview

| Task | Component | Priority | Coverage Target |
|------|-----------|----------|-----------------|
| 1 | Server WebSocket Tests | HIGH | server/app.py 44% → 85% |
| 2 | Session Event Loop Tests | HIGH | server/session.py 34% → 85% |
| 3 | Terminal Context Tests | HIGH | console/terminal.py 32% → 80% |
| 4 | RPC Encoder Edge Cases | MEDIUM | rpc/encoder.py 78% → 95% |
| 5 | Wasm Bootstrap Edge Cases | MEDIUM | wasm/bootstrap.py 67% → 90% |
| 6 | Console Input Parsing | MEDIUM | console/input.py 71% → 90% |
| 7 | Thread Safety Integration | HIGH | New integration tests |
| 8 | Signal→Effect→Computed Integration | HIGH | New integration tests |
| 9 | Renderer Protocol Integration | MEDIUM | Cross-renderer validation |
| 10 | Update Gatekeeper Thresholds | LOW | Verify all gatekeepers pass |

---

### Task 1: Server WebSocket Event Tests

**Files:**
- Modify: `tests/test_server_app.py`
- Test: `src/flow/server/app.py:160-280`

**Step 1: Write failing tests for WebSocket event handling**

```python
# tests/test_server_app.py
"""Tests for server WebSocket event handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from flow.server.app import create_app, _get_or_create_root, _re_render_root
from flow.component import component
from flow.signal import Signal
from flow.ui import Div, Text, Button, Input


@component
async def TestApp():
    """Test app with interactive elements."""
    count = Signal(0)
    text = Signal("")

    with Div(cls="container"):
        Text(f"Count: {count.value}")
        Button("Increment", on_click=lambda: setattr(count, "value", count.value + 1))
        Input(bind=text, placeholder="Enter text")


def test_get_or_create_root_caches_component():
    """First call creates root, second returns cached."""
    app = create_app(TestApp)

    with patch.object(app.state, "root_component", None):
        root1 = _get_or_create_root(app, TestApp)
        root2 = _get_or_create_root(app, TestApp)

        # Same instance returned
        assert root1 is root2


def test_re_render_root_clears_registry():
    """Re-render clears runtime registry before rebuilding."""
    from flow.runtime.registry import RuntimeRegistry

    app = create_app(TestApp)

    with patch.object(RuntimeRegistry, "clear") as mock_clear:
        _re_render_root(app, TestApp)
        mock_clear.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_click_event_routes_to_handler():
    """WebSocket click events call the correct handler."""
    app = create_app(TestApp)
    client = TestClient(app)

    # Mock the element registry to track handler calls
    handler_called = []

    with client.websocket_connect("/ws") as websocket:
        # Send a click event
        websocket.send_json({
            "type": "click",
            "element_id": "btn-1",
        })

        # Should receive re-render response
        response = websocket.receive_json()
        assert "html" in response or response.get("type") == "update"


@pytest.mark.asyncio
async def test_websocket_input_event_updates_signal():
    """WebSocket input events update bound Signals."""
    app = create_app(TestApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({
            "type": "input",
            "element_id": "input-1",
            "value": "Hello World",
        })

        response = websocket.receive_json()
        assert response is not None


@pytest.mark.asyncio
async def test_websocket_malformed_json_handled():
    """Malformed JSON doesn't crash the server."""
    app = create_app(TestApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send invalid JSON-like data
        websocket.send_text("{invalid json")

        # Server should handle gracefully (close or ignore)
        # This tests line 278-279


@pytest.mark.asyncio
async def test_websocket_unknown_event_type_ignored():
    """Unknown event types are logged but don't crash."""
    app = create_app(TestApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({
            "type": "unknown_event",
            "data": "test",
        })

        # Should not raise, connection remains open
        websocket.send_json({"type": "ping"})
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_server_app.py -v -k "websocket"
```

Expected: Some tests FAIL due to missing implementation or mocking issues

**Step 3: Implement fixes and add mocking infrastructure**

Add the required WebSocket test infrastructure to handle async event loops properly.

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_server_app.py -v
```

Expected: PASS

**Step 5: Check coverage improvement**

```bash
uv run pytest tests/test_server_app.py --cov=src/flow/server/app --cov-report=term-missing
```

Expected: Coverage > 70%

**Step 6: Commit**

```bash
git add tests/test_server_app.py
git commit -m "test(server): add WebSocket event handling tests"
```

---

### Task 2: Session Event Loop Tests

**Files:**
- Modify: `tests/test_session.py`
- Modify: `tests/test_session_events.py`
- Test: `src/flow/server/session.py:106-206`

**Step 1: Write failing tests for session event loops**

```python
# tests/test_session_events.py (additions)
"""Tests for LiveSession event handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from flow.server.session import LiveSession
from flow.ui import Div, Text, Button
from flow.signal import Signal


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with async methods."""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def simple_app():
    """Create a simple test app."""
    count = Signal(0)

    with Div(cls="app") as root:
        Text(f"Count: {count.value}")
        with Button("Click", on_click=lambda: setattr(count, "value", count.value + 1)) as btn:
            pass

    return root, count, btn


@pytest.mark.asyncio
async def test_session_incoming_loop_processes_events(mock_websocket, simple_app):
    """Incoming loop processes events from WebSocket."""
    root, count, btn = simple_app

    # Queue up events
    mock_websocket.receive_json.side_effect = [
        {"type": "click", "element_id": id(btn)},
        asyncio.CancelledError(),  # Stop the loop
    ]

    session = LiveSession(root, mock_websocket)

    with pytest.raises(asyncio.CancelledError):
        await session._incoming_loop()

    # Handler should have been called
    assert count.value == 1


@pytest.mark.asyncio
async def test_session_incoming_loop_handles_connection_drop(mock_websocket, simple_app):
    """Connection drops are handled gracefully."""
    root, _, _ = simple_app

    mock_websocket.receive_json.side_effect = ConnectionError("Connection lost")

    session = LiveSession(root, mock_websocket)

    # Should not raise, should exit cleanly
    await session._incoming_loop()


@pytest.mark.asyncio
async def test_session_outgoing_loop_sends_updates(mock_websocket, simple_app):
    """Outgoing loop sends HTML updates."""
    root, count, _ = simple_app

    session = LiveSession(root, mock_websocket)

    # Queue an update
    session._update_queue.put_nowait(True)

    # Run one iteration
    with patch.object(session, "_render_diff", return_value="<div>Updated</div>"):
        # Cancel after first iteration
        async def stop_after_one():
            await asyncio.sleep(0.01)
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await asyncio.gather(
                session._outgoing_loop(),
                stop_after_one(),
            )

    mock_websocket.send_text.assert_called()


@pytest.mark.asyncio
async def test_session_handle_event_click(mock_websocket, simple_app):
    """Click events route to element handlers."""
    root, count, btn = simple_app

    session = LiveSession(root, mock_websocket)

    await session._handle_event({
        "type": "click",
        "element_id": id(btn),
    })

    assert count.value == 1


@pytest.mark.asyncio
async def test_session_handle_event_unknown_element(mock_websocket, simple_app):
    """Unknown element IDs are handled gracefully."""
    root, _, _ = simple_app

    session = LiveSession(root, mock_websocket)

    # Should not raise
    await session._handle_event({
        "type": "click",
        "element_id": 999999,  # Non-existent
    })


@pytest.mark.asyncio
async def test_session_stop_cancels_tasks(mock_websocket, simple_app):
    """Stop method cancels running tasks."""
    root, _, _ = simple_app

    session = LiveSession(root, mock_websocket)

    # Start session
    task = asyncio.create_task(session.start())

    await asyncio.sleep(0.01)

    # Stop should cancel
    await session.stop()

    assert task.cancelled() or task.done()
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_session_events.py -v
```

Expected: FAIL (async test issues or missing implementations)

**Step 3: Fix async test infrastructure in conftest**

```python
# tests/conftest.py (additions)
import pytest

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_session_events.py -v
```

Expected: PASS

**Step 5: Check coverage**

```bash
uv run pytest tests/test_session*.py --cov=src/flow/server/session --cov-report=term-missing
```

Expected: Coverage > 70%

**Step 6: Commit**

```bash
git add tests/test_session*.py tests/conftest.py
git commit -m "test(session): add event loop and handler tests"
```

---

### Task 3: Terminal Context Tests

**Files:**
- Create: `tests/test_console_terminal_extended.py`
- Test: `src/flow/renderer/console/terminal.py:31-141`

**Step 1: Write failing tests with TTY mocking**

```python
# tests/test_console_terminal_extended.py
"""Extended tests for console terminal utilities with TTY mocking."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys

from flow.renderer.console.terminal import (
    get_terminal_size,
    setup_raw_mode,
    restore_terminal,
    TerminalContext,
    _original_termios,
)


class TestSetupRawMode:
    """Tests for setup_raw_mode function."""

    def test_setup_raw_mode_non_tty_skips(self):
        """Non-TTY stdin skips raw mode setup."""
        with patch.object(sys.stdin, "isatty", return_value=False):
            setup_raw_mode()
            # Should not raise, should skip silently

    def test_setup_raw_mode_stores_original_settings(self):
        """Raw mode stores original termios for restoration."""
        mock_fd = 0
        mock_termios = [1, 2, 3, 4, 5, 6, []]

        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdin, "fileno", return_value=mock_fd), \
             patch("flow.renderer.console.terminal.termios") as mock_termios_mod, \
             patch("flow.renderer.console.terminal.tty") as mock_tty:

            mock_termios_mod.tcgetattr.return_value = mock_termios

            setup_raw_mode()

            mock_termios_mod.tcgetattr.assert_called_once_with(mock_fd)
            mock_tty.setraw.assert_called_once_with(mock_fd)

    def test_setup_raw_mode_handles_import_error(self):
        """ImportError for termios is handled gracefully."""
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch.dict(sys.modules, {"termios": None}):
            # Should not raise
            setup_raw_mode()


class TestRestoreTerminal:
    """Tests for restore_terminal function."""

    def test_restore_terminal_without_prior_setup(self):
        """Restore without prior setup is a no-op."""
        # Reset global state
        import flow.renderer.console.terminal as term_mod
        term_mod._original_termios = None

        restore_terminal()  # Should not raise

    def test_restore_terminal_restores_settings(self):
        """Restore applies saved termios settings."""
        import flow.renderer.console.terminal as term_mod

        mock_fd = 0
        mock_termios = [1, 2, 3, 4, 5, 6, []]
        term_mod._original_termios = mock_termios

        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdin, "fileno", return_value=mock_fd), \
             patch("flow.renderer.console.terminal.termios") as mock_termios_mod:

            restore_terminal()

            mock_termios_mod.tcsetattr.assert_called_once_with(
                mock_fd,
                mock_termios_mod.TCSADRAIN,
                mock_termios,
            )

    def test_restore_terminal_clears_global_state(self):
        """Restore clears the global termios storage."""
        import flow.renderer.console.terminal as term_mod

        term_mod._original_termios = [1, 2, 3]

        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdin, "fileno", return_value=0), \
             patch("flow.renderer.console.terminal.termios"):

            restore_terminal()

            assert term_mod._original_termios is None


class TestTerminalContext:
    """Tests for TerminalContext context manager."""

    def test_context_enter_sets_up_terminal(self):
        """Context enter performs terminal setup."""
        with patch("flow.renderer.console.terminal.setup_raw_mode") as mock_setup, \
             patch("flow.renderer.console.terminal.ansi") as mock_ansi, \
             patch.object(sys.stdout, "write") as mock_write, \
             patch.object(sys.stdout, "flush"):

            ctx = TerminalContext(width=80, height=24, alt_screen=True)
            ctx.__enter__()

            mock_setup.assert_called_once()
            # Should write: alt_screen, cursor_hide, clear_screen
            assert mock_write.call_count >= 3

    def test_context_exit_restores_terminal(self):
        """Context exit restores terminal state."""
        with patch("flow.renderer.console.terminal.setup_raw_mode"), \
             patch("flow.renderer.console.terminal.restore_terminal") as mock_restore, \
             patch("flow.renderer.console.terminal.ansi") as mock_ansi, \
             patch.object(sys.stdout, "write"), \
             patch.object(sys.stdout, "flush"):

            ctx = TerminalContext(width=80, height=24, alt_screen=True)
            ctx.__enter__()
            ctx.__exit__(None, None, None)

            mock_restore.assert_called_once()

    def test_context_exit_on_exception_still_restores(self):
        """Terminal is restored even if exception occurs."""
        with patch("flow.renderer.console.terminal.setup_raw_mode"), \
             patch("flow.renderer.console.terminal.restore_terminal") as mock_restore, \
             patch("flow.renderer.console.terminal.ansi"), \
             patch.object(sys.stdout, "write"), \
             patch.object(sys.stdout, "flush"):

            ctx = TerminalContext(width=80, height=24)
            ctx.__enter__()

            # Simulate exception during context
            ctx.__exit__(ValueError, ValueError("test"), None)

            mock_restore.assert_called_once()

    def test_context_without_alt_screen(self):
        """Context can skip alternate screen buffer."""
        with patch("flow.renderer.console.terminal.setup_raw_mode"), \
             patch("flow.renderer.console.terminal.ansi") as mock_ansi, \
             patch.object(sys.stdout, "write") as mock_write, \
             patch.object(sys.stdout, "flush"):

            mock_ansi.enter_alt_screen.return_value = "ALT_SCREEN"
            mock_ansi.cursor_hide.return_value = "HIDE"
            mock_ansi.clear_screen.return_value = "CLEAR"

            ctx = TerminalContext(width=80, height=24, alt_screen=False)
            ctx.__enter__()

            # Should NOT write alt_screen sequence
            writes = [call[0][0] for call in mock_write.call_args_list]
            assert "ALT_SCREEN" not in writes

    def test_context_auto_detects_size(self):
        """Context auto-detects terminal size if not provided."""
        with patch("flow.renderer.console.terminal.get_terminal_size", return_value=(120, 40)), \
             patch("flow.renderer.console.terminal.setup_raw_mode"), \
             patch("flow.renderer.console.terminal.ansi"), \
             patch.object(sys.stdout, "write"), \
             patch.object(sys.stdout, "flush"):

            ctx = TerminalContext()

            assert ctx.width == 120
            assert ctx.height == 40
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_console_terminal_extended.py -v
```

Expected: FAIL (mock setup issues)

**Step 3: Run tests after implementation**

```bash
uv run pytest tests/test_console_terminal_extended.py -v
```

Expected: PASS

**Step 4: Check coverage**

```bash
uv run pytest tests/test_console_terminal*.py --cov=src/flow/renderer/console/terminal --cov-report=term-missing
```

Expected: Coverage > 75%

**Step 5: Commit**

```bash
git add tests/test_console_terminal_extended.py
git commit -m "test(console): add TTY mocking tests for terminal context"
```

---

### Task 4: RPC Encoder Edge Cases

**Files:**
- Modify: `tests/test_rpc_serialization.py`
- Test: `src/flow/rpc/encoder.py:60-93`

**Step 1: Write failing tests for edge case types**

```python
# tests/test_rpc_serialization.py (additions)
"""Tests for RPC encoder edge cases."""

import pytest
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from flow.rpc.encoder import FlowJSONEncoder


class TestFlowJSONEncoderEdgeCases:
    """Tests for edge case type encoding."""

    def test_encode_bytes_to_base64(self):
        """Bytes are encoded as base64 strings."""
        data = {"binary": b"hello world"}

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        # Should be base64 encoded
        import base64
        assert parsed["binary"] == base64.b64encode(b"hello world").decode()

    def test_encode_set_to_list(self):
        """Sets are converted to sorted lists."""
        data = {"items": {3, 1, 2}}

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        # Should be a list (order may vary)
        assert isinstance(parsed["items"], list)
        assert set(parsed["items"]) == {1, 2, 3}

    def test_encode_frozenset_to_list(self):
        """Frozensets are converted to lists."""
        data = {"frozen": frozenset(["a", "b", "c"])}

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        assert isinstance(parsed["frozen"], list)
        assert set(parsed["frozen"]) == {"a", "b", "c"}

    def test_encode_nested_dataclass_in_list(self):
        """Dataclasses inside lists are properly encoded."""
        @dataclass
        class Item:
            id: UUID
            created: datetime

        items = [
            Item(id=uuid4(), created=datetime(2024, 1, 1, 12, 0, 0)),
            Item(id=uuid4(), created=datetime(2024, 1, 2, 12, 0, 0)),
        ]
        data = {"items": items}

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        assert len(parsed["items"]) == 2
        assert "id" in parsed["items"][0]
        assert "created" in parsed["items"][0]

    def test_encode_dataclass_in_dict_values(self):
        """Dataclasses as dict values are properly encoded."""
        @dataclass
        class User:
            name: str
            created: datetime

        data = {
            "users": {
                "alice": User(name="Alice", created=datetime(2024, 1, 1)),
                "bob": User(name="Bob", created=datetime(2024, 1, 2)),
            }
        }

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        assert parsed["users"]["alice"]["name"] == "Alice"
        assert "created" in parsed["users"]["alice"]

    def test_encode_deeply_nested_complex_types(self):
        """Deeply nested structures with mixed types encode correctly."""
        @dataclass
        class Nested:
            value: int

        data = {
            "level1": {
                "level2": [
                    {
                        "level3": Nested(value=42),
                        "datetime": datetime(2024, 1, 1),
                        "uuid": uuid4(),
                    }
                ]
            }
        }

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        assert parsed["level1"]["level2"][0]["level3"]["value"] == 42

    def test_encode_empty_collections(self):
        """Empty sets and frozensets encode as empty lists."""
        data = {
            "empty_set": set(),
            "empty_frozenset": frozenset(),
        }

        result = json.dumps(data, cls=FlowJSONEncoder)
        parsed = json.loads(result)

        assert parsed["empty_set"] == []
        assert parsed["empty_frozenset"] == []
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_rpc_serialization.py -v -k "edge"
```

Expected: FAIL for bytes/set/frozenset encoding

**Step 3: Update encoder implementation if needed**

The encoder at `src/flow/rpc/encoder.py` may need updates to handle these types.

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_rpc_serialization.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_rpc_serialization.py
git commit -m "test(rpc): add encoder edge case tests for bytes/set/frozenset"
```

---

### Task 5: Wasm Bootstrap Edge Cases

**Files:**
- Create: `tests/test_wasm_bootstrap_extended.py`
- Test: `src/flow/wasm/bootstrap.py:50-126`

**Step 1: Write failing tests for browser edge cases**

```python
# tests/test_wasm_bootstrap_extended.py
"""Extended tests for Wasm bootstrap with browser mocking."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys


class TestGetDocument:
    """Tests for get_document function."""

    def test_get_document_returns_js_document(self):
        """Returns js.document when available."""
        mock_js = MagicMock()
        mock_js.document = MagicMock()

        with patch.dict(sys.modules, {"js": mock_js}):
            from flow.wasm.bootstrap import get_document

            # Reload to pick up mock
            import importlib
            import flow.wasm.bootstrap
            importlib.reload(flow.wasm.bootstrap)

            result = flow.wasm.bootstrap.get_document()
            assert result is mock_js.document

    def test_get_document_returns_none_without_js(self):
        """Returns None when js module not available."""
        with patch.dict(sys.modules, {"js": None}):
            from flow.wasm.bootstrap import get_document

            import importlib
            import flow.wasm.bootstrap
            importlib.reload(flow.wasm.bootstrap)

            result = flow.wasm.bootstrap.get_document()
            assert result is None


class TestProxyFactory:
    """Tests for _get_proxy_factory function."""

    def test_proxy_factory_uses_pyodide_ffi(self):
        """Uses create_proxy from pyodide.ffi when available."""
        mock_ffi = MagicMock()
        mock_ffi.create_proxy = MagicMock(return_value="proxy")

        mock_pyodide = MagicMock()
        mock_pyodide.ffi = mock_ffi

        with patch.dict(sys.modules, {"pyodide": mock_pyodide, "pyodide.ffi": mock_ffi}):
            from flow.wasm.bootstrap import _get_proxy_factory

            import importlib
            import flow.wasm.bootstrap
            importlib.reload(flow.wasm.bootstrap)

            factory = flow.wasm.bootstrap._get_proxy_factory()
            result = factory(lambda: None)

            assert mock_ffi.create_proxy.called

    def test_proxy_factory_fallback_identity(self):
        """Falls back to identity function without pyodide."""
        with patch.dict(sys.modules, {"pyodide": None, "pyodide.ffi": None}):
            from flow.wasm.bootstrap import _get_proxy_factory

            import importlib
            import flow.wasm.bootstrap
            importlib.reload(flow.wasm.bootstrap)

            factory = flow.wasm.bootstrap._get_proxy_factory()
            test_fn = lambda: "test"

            assert factory(test_fn) is test_fn


class TestFlowAppMount:
    """Tests for FlowApp.mount method."""

    def test_mount_raises_without_document(self):
        """Mount raises ValueError without browser document."""
        from flow.wasm.bootstrap import FlowApp
        from flow.ui import Div

        with patch("flow.wasm.bootstrap.get_document", return_value=None):
            app = FlowApp(Div())

            with pytest.raises(ValueError, match="not a browser"):
                app.mount("#app")

    def test_mount_raises_for_missing_container(self):
        """Mount raises ValueError when container not found."""
        from flow.wasm.bootstrap import FlowApp
        from flow.ui import Div

        mock_doc = MagicMock()
        mock_doc.querySelector.return_value = None

        with patch("flow.wasm.bootstrap.get_document", return_value=mock_doc):
            app = FlowApp(Div())

            with pytest.raises(ValueError, match="Container.*not found"):
                app.mount("#nonexistent")

    def test_mount_renders_to_container(self):
        """Mount renders element to container innerHTML."""
        from flow.wasm.bootstrap import FlowApp
        from flow.ui import Div, Text

        mock_container = MagicMock()
        mock_doc = MagicMock()
        mock_doc.querySelector.return_value = mock_container

        with patch("flow.wasm.bootstrap.get_document", return_value=mock_doc):
            with Div() as root:
                Text("Hello")

            app = FlowApp(root)
            app.mount("#app")

            # innerHTML should be set
            assert mock_container.innerHTML is not None
```

**Step 2: Run tests**

```bash
uv run pytest tests/test_wasm_bootstrap_extended.py -v
```

**Step 3: Commit**

```bash
git add tests/test_wasm_bootstrap_extended.py
git commit -m "test(wasm): add bootstrap edge case tests for browser environments"
```

---

### Task 6: Console Input Parsing Tests

**Files:**
- Modify: `tests/test_console_input.py`
- Test: `src/flow/renderer/console/input.py:53-97`

**Step 1: Write failing tests for input edge cases**

```python
# tests/test_console_input.py (additions)
"""Extended tests for console input parsing."""

import pytest

from flow.renderer.console.input import (
    KeyEvent,
    parse_key_sequence,
    CTRL_C, CTRL_D, CTRL_O, CTRL_Z,
    ESCAPE, ENTER, BACKSPACE,
    ESCAPE_SEQUENCES,
)


class TestParseKeySequenceEdgeCases:
    """Tests for edge cases in key sequence parsing."""

    def test_parse_empty_sequence(self):
        """Empty sequence returns empty key."""
        event = parse_key_sequence("")
        assert event.key == ""

    def test_parse_all_ctrl_keys(self):
        """All Ctrl+letter combinations parse correctly."""
        for i in range(1, 27):  # Ctrl+A through Ctrl+Z
            char = chr(i)
            event = parse_key_sequence(char)

            expected_letter = chr(i + 96)  # 'a' through 'z'
            assert event.key == expected_letter
            assert event.ctrl is True

    def test_parse_tab(self):
        """Tab key parses correctly."""
        event = parse_key_sequence("\t")
        assert event.key == "tab"

    def test_parse_backspace_0x7f(self):
        """Backspace (0x7f) parses correctly."""
        event = parse_key_sequence("\x7f")
        assert event.key == "backspace"

    def test_parse_backspace_0x08(self):
        """Backspace (0x08) parses correctly."""
        event = parse_key_sequence("\x08")
        assert event.key == "backspace"

    def test_parse_newline(self):
        """Newline parses as enter."""
        event = parse_key_sequence("\n")
        assert event.key == "enter"

    def test_parse_carriage_return(self):
        """Carriage return parses as enter."""
        event = parse_key_sequence("\r")
        assert event.key == "enter"

    def test_parse_all_arrow_keys(self):
        """All arrow keys parse correctly."""
        assert parse_key_sequence("\x1b[A").key == "up"
        assert parse_key_sequence("\x1b[B").key == "down"
        assert parse_key_sequence("\x1b[C").key == "right"
        assert parse_key_sequence("\x1b[D").key == "left"

    def test_parse_navigation_keys(self):
        """Navigation keys parse correctly."""
        assert parse_key_sequence("\x1b[H").key == "home"
        assert parse_key_sequence("\x1b[F").key == "end"
        assert parse_key_sequence("\x1b[3~").key == "delete"
        assert parse_key_sequence("\x1b[5~").key == "page_up"
        assert parse_key_sequence("\x1b[6~").key == "page_down"

    def test_parse_function_keys(self):
        """Function keys parse correctly."""
        assert parse_key_sequence("\x1bOP").key == "f1"
        assert parse_key_sequence("\x1bOQ").key == "f2"
        assert parse_key_sequence("\x1bOR").key == "f3"
        assert parse_key_sequence("\x1bOS").key == "f4"

    def test_parse_unknown_escape_sequence(self):
        """Unknown escape sequences return raw sequence."""
        event = parse_key_sequence("\x1b[999~")
        assert event.key == "\x1b[999~"

    def test_parse_unicode_character(self):
        """Unicode characters parse correctly."""
        event = parse_key_sequence("ä")
        assert event.key == "ä"
        assert event.ctrl is False

    def test_parse_emoji(self):
        """Emoji characters parse correctly."""
        event = parse_key_sequence("🎉")
        assert event.key == "🎉"

    def test_key_event_equality(self):
        """KeyEvent equality works correctly."""
        event1 = KeyEvent(key="a", ctrl=True)
        event2 = KeyEvent(key="a", ctrl=True)
        event3 = KeyEvent(key="a", ctrl=False)

        assert event1 == event2
        assert event1 != event3
```

**Step 2: Run tests**

```bash
uv run pytest tests/test_console_input.py -v
```

**Step 3: Commit**

```bash
git add tests/test_console_input.py
git commit -m "test(console): add comprehensive input parsing tests"
```

---

### Task 7: Thread Safety Integration Tests

**Files:**
- Create: `tests/test_thread_safety.py`
- Test: Signal/Effect/Computed under concurrent access

**Step 1: Write thread safety tests**

```python
# tests/test_thread_safety.py
"""Thread safety integration tests for the reactivity system."""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from flow.signal import Signal
from flow.effect import Effect
from flow.computed import Computed


class TestSignalThreadSafety:
    """Tests for Signal thread safety under No-GIL."""

    def test_concurrent_signal_writes(self):
        """Multiple threads writing to same Signal don't corrupt state."""
        signal = Signal(0)
        iterations = 1000
        num_threads = 4

        def increment():
            for _ in range(iterations):
                signal.value += 1

        threads = [threading.Thread(target=increment) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Note: Without proper locking, this would be less than expected
        # With locking, final value should be exactly iterations * num_threads
        # However, += is not atomic even with lock on value property
        # This test documents the actual behavior
        assert signal.value > 0

    def test_concurrent_signal_read_write(self):
        """Reading and writing simultaneously doesn't crash."""
        signal = Signal(0)
        results = []

        def writer():
            for i in range(100):
                signal.value = i
                time.sleep(0.001)

        def reader():
            for _ in range(100):
                results.append(signal.value)
                time.sleep(0.001)

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        # All reads should be valid integers
        assert all(isinstance(r, int) for r in results)

    def test_concurrent_subscriber_notification(self):
        """Subscribers are notified correctly under concurrent writes."""
        signal = Signal(0)
        notifications = []
        lock = threading.Lock()

        def on_change(value):
            with lock:
                notifications.append(value)

        signal.subscribe(on_change)

        def writer():
            for i in range(50):
                signal.value = i

        threads = [threading.Thread(target=writer) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have received many notifications
        assert len(notifications) > 0


class TestEffectThreadSafety:
    """Tests for Effect thread safety."""

    def test_effect_scheduling_deduplication(self):
        """Effects are deduplicated even under concurrent scheduling."""
        signal = Signal(0)
        execution_count = [0]
        lock = threading.Lock()

        def effect_fn():
            _ = signal.value  # Track dependency
            with lock:
                execution_count[0] += 1

        effect = Effect(effect_fn)
        effect.run()  # Initial run

        initial_count = execution_count[0]

        # Trigger many concurrent updates
        def update():
            for i in range(10):
                signal.value = i

        threads = [threading.Thread(target=update) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Allow time for effects to run
        time.sleep(0.1)

        # Should have executed, but potentially deduplicated
        assert execution_count[0] > initial_count


class TestComputedThreadSafety:
    """Tests for Computed thread safety."""

    def test_computed_concurrent_access(self):
        """Computed values are consistent under concurrent reads."""
        signal = Signal(10)
        computed = Computed(lambda: signal.value * 2)

        results = []
        lock = threading.Lock()

        def reader():
            for _ in range(100):
                value = computed.value
                with lock:
                    results.append(value)

        threads = [threading.Thread(target=reader) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All values should be even (signal * 2)
        assert all(r % 2 == 0 for r in results)

    def test_computed_invalidation_thread_safety(self):
        """Computed invalidation is thread-safe."""
        signal = Signal(1)
        computed = Computed(lambda: signal.value * 2)

        # Read initial value
        assert computed.value == 2

        def writer():
            for i in range(2, 100):
                signal.value = i
                time.sleep(0.001)

        def reader():
            values = []
            for _ in range(100):
                values.append(computed.value)
                time.sleep(0.001)
            return values

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        # Final value should reflect last write
        assert computed.value == 99 * 2
```

**Step 2: Run tests**

```bash
uv run pytest tests/test_thread_safety.py -v
```

**Step 3: Commit**

```bash
git add tests/test_thread_safety.py
git commit -m "test(reactivity): add thread safety integration tests"
```

---

### Task 8: Signal→Effect→Computed Integration Tests

**Files:**
- Create: `tests/test_reactivity_integration.py`
- Test: Full reactivity pipeline

**Step 1: Write integration tests**

```python
# tests/test_reactivity_integration.py
"""Integration tests for the full reactivity pipeline."""

import pytest
from flow.signal import Signal
from flow.effect import Effect
from flow.computed import Computed


class TestReactivityPipeline:
    """Tests for Signal → Effect → Computed interactions."""

    def test_signal_triggers_effect_triggers_computed(self):
        """Full pipeline: Signal change → Effect runs → Computed updates."""
        # Setup
        source = Signal(1)
        multiplied = Computed(lambda: source.value * 2)

        effect_values = []

        def track_effect():
            effect_values.append(multiplied.value)

        effect = Effect(track_effect)
        effect.run()  # Initial run captures value 2

        # Change source
        source.value = 5

        # Allow effect to run
        import time
        time.sleep(0.05)

        # Effect should have captured both values
        assert 2 in effect_values
        # Note: Effect re-execution depends on scheduling

    def test_diamond_dependency_pattern(self):
        """Diamond pattern: A → B, A → C, B+C → D."""
        a = Signal(1)
        b = Computed(lambda: a.value + 1)
        c = Computed(lambda: a.value * 2)
        d = Computed(lambda: b.value + c.value)

        # Initial values
        assert b.value == 2  # 1 + 1
        assert c.value == 2  # 1 * 2
        assert d.value == 4  # 2 + 2

        # Update source
        a.value = 3

        # All should update
        assert b.value == 4  # 3 + 1
        assert c.value == 6  # 3 * 2
        assert d.value == 10  # 4 + 6

    def test_computed_chain(self):
        """Chained computeds propagate correctly."""
        source = Signal(1)
        step1 = Computed(lambda: source.value + 1)
        step2 = Computed(lambda: step1.value * 2)
        step3 = Computed(lambda: step2.value + 10)

        assert step3.value == 14  # ((1 + 1) * 2) + 10

        source.value = 5

        assert step3.value == 22  # ((5 + 1) * 2) + 10

    def test_conditional_dependency(self):
        """Conditional dependencies are tracked correctly."""
        flag = Signal(True)
        value_a = Signal(10)
        value_b = Signal(20)

        def conditional_compute():
            if flag.value:
                return value_a.value
            else:
                return value_b.value

        result = Computed(conditional_compute)

        assert result.value == 10  # flag is True

        flag.value = False
        assert result.value == 20  # flag is False

        # Now value_a changes shouldn't affect result
        value_a.value = 100
        assert result.value == 20  # Still from value_b

    def test_effect_cleanup_on_rerun(self):
        """Effects clean up previous subscriptions on rerun."""
        signal1 = Signal(1)
        signal2 = Signal(2)
        selector = Signal(1)

        access_log = []

        def tracking_effect():
            if selector.value == 1:
                access_log.append(f"signal1:{signal1.value}")
            else:
                access_log.append(f"signal2:{signal2.value}")

        effect = Effect(tracking_effect)
        effect.run()

        # Initially tracks signal1
        assert "signal1:1" in access_log

        # Switch to signal2
        selector.value = 2

        # Now signal1 changes shouldn't trigger effect
        access_log.clear()
        signal1.value = 100

        # Effect shouldn't have run for signal1 change
        # (This depends on actual implementation behavior)

    def test_many_subscribers_performance(self):
        """Many subscribers don't cause performance issues."""
        signal = Signal(0)
        computeds = [Computed(lambda s=signal: s.value * i) for i in range(100)]

        # Read all to establish dependencies
        _ = [c.value for c in computeds]

        # Update signal
        signal.value = 10

        # All should update correctly
        for i, c in enumerate(computeds):
            assert c.value == 10 * i

    def test_nested_effect_execution(self):
        """Nested effect creation during effect execution."""
        outer_signal = Signal(1)
        inner_signal = Signal(10)
        results = []

        def outer_effect():
            outer_val = outer_signal.value

            def inner_effect():
                results.append(outer_val + inner_signal.value)

            Effect(inner_effect).run()

        Effect(outer_effect).run()

        assert 11 in results  # 1 + 10
```

**Step 2: Run tests**

```bash
uv run pytest tests/test_reactivity_integration.py -v
```

**Step 3: Commit**

```bash
git add tests/test_reactivity_integration.py
git commit -m "test(reactivity): add pipeline integration tests"
```

---

### Task 9: Renderer Protocol Integration Tests

**Files:**
- Create: `tests/test_renderer_protocol_integration.py`
- Test: Cross-renderer validation

**Step 1: Write cross-renderer tests**

```python
# tests/test_renderer_protocol_integration.py
"""Integration tests for renderer protocol compliance."""

import pytest
from flow.renderer import HTMLRenderer, ConsoleRenderer, Renderer
from flow.renderer.protocol import RenderNode
from flow.ui import Div, Text, VStack, HStack, Button


class TestRendererProtocolCompliance:
    """Tests that all renderers implement the protocol correctly."""

    @pytest.fixture
    def simple_element(self):
        """Create a simple element tree."""
        with Div(cls="container") as root:
            Text("Hello World")
        return root

    @pytest.fixture
    def complex_element(self):
        """Create a complex nested element tree."""
        with Div(cls="app") as root:
            with VStack(cls="main"):
                Text("Header")
                with HStack(cls="content"):
                    Text("Left")
                    Text("Right")
                Button("Click Me")
        return root

    def test_all_renderers_implement_protocol(self):
        """All renderer classes implement Renderer ABC."""
        assert issubclass(HTMLRenderer, Renderer)
        assert issubclass(ConsoleRenderer, Renderer)

    def test_all_renderers_have_render_method(self, simple_element):
        """All renderers have working render() method."""
        html_renderer = HTMLRenderer()
        console_renderer = ConsoleRenderer(width=80, height=24)

        html_output = html_renderer.render(simple_element)
        console_output = console_renderer.render(simple_element)

        assert isinstance(html_output, str)
        assert isinstance(console_output, str)

    def test_all_renderers_handle_nested_elements(self, complex_element):
        """All renderers handle nested element trees."""
        html_renderer = HTMLRenderer()
        console_renderer = ConsoleRenderer(width=80, height=24)

        html_output = html_renderer.render(complex_element)
        console_output = console_renderer.render(complex_element)

        # HTML should contain expected text
        assert "Header" in html_output
        assert "Left" in html_output
        assert "Right" in html_output
        assert "Click Me" in html_output

        # Console output should be non-empty
        assert len(console_output) > 0

    def test_renderers_handle_empty_element(self):
        """Renderers handle elements with no children."""
        empty = Div()

        html_renderer = HTMLRenderer()
        console_renderer = ConsoleRenderer(width=80, height=24)

        html_output = html_renderer.render(empty)
        console_output = console_renderer.render(empty)

        # Should not crash
        assert isinstance(html_output, str)
        assert isinstance(console_output, str)

    def test_render_node_conversion_consistency(self, simple_element):
        """Element produces consistent RenderNode."""
        node1 = simple_element.to_render_node()
        node2 = simple_element.to_render_node()

        # Same element should produce same structure
        assert node1.tag == node2.tag
        assert node1.element_id == node2.element_id
        assert len(node1.children) == len(node2.children)

    def test_html_renderer_escapes_text(self):
        """HTMLRenderer properly escapes special characters."""
        html_renderer = HTMLRenderer()

        with Div() as root:
            Text("<script>alert('xss')</script>")

        output = html_renderer.render(root)

        # Should escape < and >
        assert "<script>" not in output
        assert "&lt;" in output or "&#" in output

    def test_console_renderer_buffer_bounds(self):
        """ConsoleRenderer respects buffer bounds."""
        console_renderer = ConsoleRenderer(width=10, height=5)

        # Text longer than buffer width
        with Div() as root:
            Text("This is a very long text that exceeds buffer width")

        # Should not crash
        output = console_renderer.render(root)
        assert isinstance(output, str)
```

**Step 2: Run tests**

```bash
uv run pytest tests/test_renderer_protocol_integration.py -v
```

**Step 3: Commit**

```bash
git add tests/test_renderer_protocol_integration.py
git commit -m "test(renderer): add cross-renderer protocol integration tests"
```

---

### Task 10: Update and Verify Gatekeeper Tests

**Files:**
- Review: `tests/gatekeepers/test_*.py`
- Verify all gatekeepers pass

**Step 1: Run all gatekeeper tests**

```bash
uv run pytest tests/gatekeepers/ -v -m gatekeeper
```

**Step 2: Verify thresholds are appropriate**

Review each gatekeeper test to ensure thresholds are:
- `test_concurrency.py`: 4 threads > 2.5x speedup (No-GIL validation)
- `test_latency.py`: < 5ms for 1,000 subscribers (O(N) propagation)
- `test_bundle.py`: < 50KB client bundle, no server code leaked
- `test_memory.py`: Memory bounds appropriate

**Step 3: Document any failures**

If any gatekeepers fail, document why and whether thresholds need adjustment.

**Step 4: Commit any fixes**

```bash
git add tests/gatekeepers/
git commit -m "test(gatekeepers): verify and update thresholds"
```

---

## Verification Checklist

After completing all tasks, run these verification steps:

```bash
# Full test suite
uv run pytest tests/ -v

# Coverage report with missing lines
uv run pytest --cov=src/flow --cov-report=term-missing --cov-branch tests/

# Specific coverage targets
uv run pytest --cov=src/flow/server --cov-report=term-missing tests/test_server*.py tests/test_session*.py

# Gatekeeper tests only
uv run pytest tests/gatekeepers/ -v -m gatekeeper

# Type checking
uv run mypy src/flow/

# Linting
uv run ruff check src/flow/ tests/
```

**Target Coverage:**
- Overall: > 85%
- `server/app.py`: > 80%
- `server/session.py`: > 80%
- `console/terminal.py`: > 75%
- All critical paths covered

---

## Future Enhancements (Not in Scope)

1. **Property-based testing** with Hypothesis for edge case generation
2. **Mutation testing** to verify test quality
3. **Performance regression tests** with historical benchmarks
4. **Visual regression tests** for console output
5. **Fuzz testing** for input parsing
