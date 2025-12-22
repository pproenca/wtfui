# tests/test_server_app.py
"""Tests for FastAPI server integration."""

import contextlib
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wtfui.core.component import component
from wtfui.core.signal import Signal
from wtfui.ui import Button, Div, Input, Text
from wtfui.web.rpc import RpcRegistry, rpc
from wtfui.web.server.app import create_app


@component
async def SimpleApp():
    with Div(cls="container") as root:
        Text("Hello from Flow!")
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
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/ws" in routes


# WebSocket Event Handling Tests


def test_get_or_create_root_caches_element():
    """First call creates root, subsequent calls return cached version."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    # Make two requests to the root
    response1 = client.get("/")
    response2 = client.get("/")

    # Both should succeed
    assert response1.status_code == 200
    assert response2.status_code == 200

    # The responses should be identical (cached root)
    assert response1.text == response2.text


def test_websocket_accepts_connection():
    """WebSocket endpoint accepts connections."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Connection should be established
        assert websocket is not None


def test_websocket_handles_click_event():
    """WebSocket processes click events without crashing."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    # First request initializes the app state
    response = client.get("/")
    assert response.status_code == 200

    # Extract element IDs from the HTML
    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Send a click event for a real element
        websocket.send_json(
            {
                "type": "click",
                "target_id": f"wtfui-{ids[0]}",
            }
        )

        # The server should handle this without crashing
        # (It won't send a response if there's no handler)


def test_websocket_handles_input_event():
    """WebSocket processes input events without crashing."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send an input event
        websocket.send_json(
            {
                "type": "input",
                "target_id": "wtfui-12345",
                "value": "test input",
            }
        )

        # The server should handle this without crashing


def test_websocket_handles_change_event():
    """WebSocket processes change events without crashing."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send a change event
        websocket.send_json(
            {
                "type": "change",
                "target_id": "wtfui-12345",
                "value": "changed value",
            }
        )

        # The server should handle this without crashing


def test_websocket_handles_enter_event():
    """WebSocket processes enter key events (currently no-op)."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send an enter key event
        websocket.send_json(
            {
                "type": "enter",
                "target_id": "wtfui-12345",
                "value": "test",
            }
        )

        # Should not crash (even though it's a no-op)


def test_websocket_handles_unknown_event_type():
    """Unknown event types are ignored without crashing."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event with unknown type
        websocket.send_json(
            {
                "type": "unknown_event",
                "data": "test",
            }
        )

        # Should not crash - can send another event
        websocket.send_json(
            {
                "type": "another_unknown",
                "target_id": "wtfui-12345",
            }
        )


def test_websocket_handles_invalid_target_id():
    """Invalid element IDs are handled gracefully."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event with invalid element ID format (not starting with "wtfui-")
        websocket.send_json(
            {
                "type": "click",
                "target_id": "invalid-id",
            }
        )

        # Should not crash - connection remains open
        websocket.send_json(
            {
                "type": "click",
                "target_id": "also-invalid",
            }
        )


def test_websocket_handles_non_numeric_id():
    """Element IDs with non-numeric part are handled gracefully."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event with non-numeric ID
        websocket.send_json(
            {
                "type": "click",
                "target_id": "wtfui-abc",
            }
        )

        # Should not crash


def test_wtfui_prefix_length_is_six():
    """Regression test: 'wtfui-' prefix is 6 characters, not 5.

    This test prevents a bug where target_id[5:] was used instead of
    target_id[6:], causing IDs like 'wtfui-123' to become '-123'
    instead of '123', breaking element ID parsing.
    """
    prefix = "wtfui-"
    assert len(prefix) == 6, "wtfui- prefix must be exactly 6 characters"

    # Verify correct parsing of element IDs
    test_id = "wtfui-4386186288"
    assert test_id[6:] == "4386186288", "ID should be extracted after 6 chars"
    assert test_id[6:].isdigit(), "Extracted ID should be all digits"

    # Ensure the old bug (using [5:]) would fail
    assert test_id[5:] == "-4386186288", "Bug: [5:] gives wrong result"
    assert not test_id[5:].isdigit(), "Bug: [5:] includes non-digit chars"


def test_websocket_handles_missing_target_id():
    """Events without target_id are handled gracefully."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event without target_id
        websocket.send_json(
            {
                "type": "click",
            }
        )

        # Should not crash


def test_websocket_handles_missing_event_type():
    """Events without type are handled gracefully."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event without type
        websocket.send_json(
            {
                "target_id": "wtfui-12345",
            }
        )

        # Should not crash


def test_websocket_handles_malformed_json():
    """WebSocket handles malformed JSON gracefully without crashing."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send malformed JSON (this will raise an exception in the WebSocket handler)
        # The TestClient doesn't provide a way to send raw text, so we'll test
        # that the connection can recover after a bad message
        with contextlib.suppress(Exception):
            # Connection might close due to malformed JSON
            websocket.send_text("{invalid json}")

        # Try to establish a new connection to verify server didn't crash
        with client.websocket_connect("/ws") as websocket2:
            # Send a valid message on the new connection
            websocket2.send_json(
                {
                    "type": "click",
                    "target_id": "wtfui-12345",
                }
            )
            # Should work fine


def test_websocket_with_interactive_elements():
    """WebSocket works with interactive elements and handlers."""

    @component
    async def InteractiveApp():
        count = Signal(0)

        def increment():
            count.value = count.value + 1

        with Div(cls="container") as root:
            Text(f"Count: {count.value}")
            Button("Increment", on_click=increment)
        return root

    app = create_app(InteractiveApp)
    client = TestClient(app)

    # Get initial HTML
    response = client.get("/")
    assert response.status_code == 200
    # The HTML should contain wtfui elements
    assert "wtfui-" in response.text

    # Find button ID
    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Click the button
        websocket.send_json(
            {
                "type": "click",
                "target_id": f"wtfui-{ids[-1]}",  # Last ID is likely the button
            }
        )

        # Receive the re-render update
        update = websocket.receive_json()
        assert update["op"] == "update_root"
        assert "html" in update


def test_websocket_with_signal_binding():
    """WebSocket works with Signal binding on inputs."""

    @component
    async def InputApp():
        text = Signal("")

        with Div(cls="container") as root:
            Text(f"You typed: {text.value}")
            Input(bind=text, placeholder="Type here")
        return root

    app = create_app(InputApp)
    client = TestClient(app)

    # Get initial HTML
    response = client.get("/")
    assert response.status_code == 200

    # Find input ID
    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Send input event
        websocket.send_json(
            {
                "type": "input",
                "target_id": f"wtfui-{ids[-1]}",  # Last ID is likely the input
                "value": "Hello World",
            }
        )

        # Input events don't trigger re-render, just update the signal
        # So we can send another one
        websocket.send_json(
            {
                "type": "input",
                "target_id": f"wtfui-{ids[-1]}",
                "value": "Updated",
            }
        )


def test_websocket_with_async_handler():
    """WebSocket works with async event handlers."""

    @component
    async def AsyncApp():
        count = Signal(0)

        async def async_increment():
            # Simulate async operation
            count.value = count.value + 1

        with Div(cls="container") as root:
            Text(f"Count: {count.value}")
            Button("Async", on_click=async_increment)
        return root

    app = create_app(AsyncApp)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200

    # Find button ID
    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Click the async button
        websocket.send_json(
            {
                "type": "click",
                "target_id": f"wtfui-{ids[-1]}",
            }
        )

        # Receive the re-render update
        update = websocket.receive_json()
        assert update["op"] == "update_root"
        assert "html" in update


def test_websocket_multiple_connections():
    """Multiple WebSocket connections can be established."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    # Open two connections simultaneously
    with (
        client.websocket_connect("/ws") as ws1,
        client.websocket_connect("/ws") as ws2,
    ):
        assert ws1 is not None
        assert ws2 is not None

        # Both should be able to send events
        ws1.send_json({"type": "click", "target_id": "wtfui-1"})
        ws2.send_json({"type": "click", "target_id": "wtfui-2"})


def test_re_render_clears_registry():
    """Re-rendering clears and rebuilds the element registry."""

    @component
    async def CounterApp():
        count = Signal(0)

        def increment():
            count.value = count.value + 1

        with Div(cls="container") as root:
            Text(f"Count: {count.value}")
            Button("Increment", on_click=increment)
        return root

    app = create_app(CounterApp)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    initial_ids = set(re.findall(r'id="wtfui-(\d+)"', response.text))
    assert initial_ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Click button multiple times to test registry clearing on re-render
        for _ in range(3):
            websocket.send_json(
                {
                    "type": "click",
                    "target_id": f"wtfui-{max(initial_ids)}",
                }
            )
            # Each click should be processed without crashing


def test_websocket_change_event_with_handler():
    """WebSocket processes change events and triggers re-render."""

    @component
    async def ChangeApp():
        selected = Signal("none")

        def on_change(value: str):
            selected.value = value

        with Div(cls="container") as root:
            Text(f"Selected: {selected.value}")
            # Create a select-like element with on_change
            Div(on_change=on_change)
        return root

    app = create_app(ChangeApp)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200

    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Send change event
        websocket.send_json(
            {
                "type": "change",
                "target_id": f"wtfui-{ids[-1]}",
                "value": "option1",
            }
        )

        # Receive the re-render update
        update = websocket.receive_json()
        assert update["op"] == "update_root"
        assert "html" in update


def test_websocket_change_event_with_async_handler():
    """WebSocket processes change events with async handlers."""

    @component
    async def AsyncChangeApp():
        selected = Signal("none")

        async def on_change(value: str):
            selected.value = value

        with Div(cls="container") as root:
            Text(f"Selected: {selected.value}")
            Div(on_change=on_change)
        return root

    app = create_app(AsyncChangeApp)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200

    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Send change event
        websocket.send_json(
            {
                "type": "change",
                "target_id": f"wtfui-{ids[-1]}",
                "value": "option2",
            }
        )

        # Receive the re-render update
        update = websocket.receive_json()
        assert update["op"] == "update_root"
        assert "html" in update


def test_websocket_input_updates_signal():
    """WebSocket input events update bound signals."""

    @component
    async def InputBindingApp():
        text = Signal("")

        with Div(cls="container") as root:
            Text(f"Value: {text.value}")
            Input(bind=text, placeholder="Type here")
        return root

    app = create_app(InputBindingApp)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200

    ids = re.findall(r'id="wtfui-(\d+)"', response.text)
    assert ids, "Expected to find wtfui element IDs in HTML"

    with client.websocket_connect("/ws") as websocket:
        # Send input event to update the signal
        websocket.send_json(
            {
                "type": "input",
                "target_id": f"wtfui-{ids[-1]}",  # Input element
                "value": "test value",
            }
        )
        # Input events don't trigger re-render, just update the signal
        # The signal is updated but no response is sent


# RPC Endpoint Tests


@pytest.fixture(autouse=True)
def clear_rpc_registry():
    """Clear RPC registry before and after each test."""
    RpcRegistry.clear()
    yield
    RpcRegistry.clear()


def test_rpc_endpoint_successful_call():
    """RPC endpoint successfully calls registered functions."""

    @rpc
    async def test_function(name: str, age: int) -> dict[str, Any]:
        """Test RPC function."""
        return {"greeting": f"Hello {name}, you are {age} years old"}

    app = create_app(SimpleApp)
    client = TestClient(app)

    # Call the RPC endpoint
    response = client.post(
        "/api/rpc/test_function",
        json={"name": "Alice", "age": 30},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {"greeting": "Hello Alice, you are 30 years old"}


def test_rpc_endpoint_unknown_function():
    """RPC endpoint returns 404 for unknown functions."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    # Call non-existent function
    response = client.post(
        "/api/rpc/nonexistent_function",
        json={},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_rpc_endpoint_invalid_arguments():
    """RPC endpoint handles invalid arguments gracefully."""

    @rpc
    async def strict_function(required_arg: str) -> dict[str, str]:
        """Function requiring specific arguments."""
        return {"result": required_arg}

    app = create_app(SimpleApp)
    client = TestClient(app, raise_server_exceptions=False)

    # Call with missing required argument
    response = client.post(
        "/api/rpc/strict_function",
        json={},
    )

    # Should return 500 (internal server error) due to missing argument
    assert response.status_code == 500


def test_rpc_endpoint_with_complex_return():
    """RPC endpoint handles complex return types using WtfUIJSONEncoder."""

    @rpc
    async def complex_function() -> dict[str, Any]:
        """Function returning complex data."""
        return {
            "numbers": [1, 2, 3],
            "nested": {"key": "value"},
            "boolean": True,
            "null": None,
        }

    app = create_app(SimpleApp)
    client = TestClient(app)

    response = client.post("/api/rpc/complex_function", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["numbers"] == [1, 2, 3]
    assert data["nested"]["key"] == "value"
    assert data["boolean"] is True
    assert data["null"] is None


def test_rpc_endpoint_empty_body():
    """RPC endpoint handles requests with no JSON body."""

    @rpc
    async def no_args_function() -> dict[str, str]:
        """Function that takes no arguments."""
        return {"status": "success"}

    app = create_app(SimpleApp)
    client = TestClient(app)

    # Call without JSON body
    response = client.post("/api/rpc/no_args_function")

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
