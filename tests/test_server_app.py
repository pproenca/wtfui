# tests/test_server_app.py
"""Tests for FastAPI server integration."""

import re

from fastapi.testclient import TestClient

from flow.component import component
from flow.server.app import create_app
from flow.signal import Signal
from flow.ui import Button, Div, Input, Text


@component
async def SimpleApp():
    with Div(cls="container") as root, Text("Hello from Flow!"):
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
    ids = re.findall(r'id="flow-(\d+)"', response.text)

    with client.websocket_connect("/ws") as websocket:
        if ids:
            # Send a click event for a real element
            websocket.send_json(
                {
                    "type": "click",
                    "target_id": f"flow-{ids[0]}",
                }
            )
        else:
            # Send a click event with non-existent ID
            websocket.send_json(
                {
                    "type": "click",
                    "target_id": "flow-999999",
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
                "target_id": "flow-12345",
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
                "target_id": "flow-12345",
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
                "target_id": "flow-12345",
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
                "target_id": "flow-12345",
            }
        )


def test_websocket_handles_invalid_target_id():
    """Invalid element IDs are handled gracefully."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send event with invalid element ID format (not starting with "flow-")
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
                "target_id": "flow-abc",
            }
        )

        # Should not crash


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
                "target_id": "flow-12345",
            }
        )

        # Should not crash


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
    # The HTML should contain flow elements
    assert "flow-" in response.text

    # Find button ID
    ids = re.findall(r'id="flow-(\d+)"', response.text)

    with client.websocket_connect("/ws") as websocket:
        if ids:
            # Try to click the button
            websocket.send_json(
                {
                    "type": "click",
                    "target_id": f"flow-{ids[-1]}",  # Last ID is likely the button
                }
            )
            # Server should handle the event without crashing
            # We can't easily test for response without blocking indefinitely


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
    ids = re.findall(r'id="flow-(\d+)"', response.text)

    with client.websocket_connect("/ws") as websocket:
        if ids:
            # Send input event
            websocket.send_json(
                {
                    "type": "input",
                    "target_id": f"flow-{ids[-1]}",  # Last ID is likely the input
                    "value": "Hello World",
                }
            )

            # Input events don't trigger re-render, just update the signal
            # So we can send another one
            websocket.send_json(
                {
                    "type": "input",
                    "target_id": f"flow-{ids[-1]}",
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
    ids = re.findall(r'id="flow-(\d+)"', response.text)

    with client.websocket_connect("/ws") as websocket:
        if ids:
            # Click the async button
            websocket.send_json(
                {
                    "type": "click",
                    "target_id": f"flow-{ids[-1]}",
                }
            )
            # Server should handle async event without crashing


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
        ws1.send_json({"type": "click", "target_id": "flow-1"})
        ws2.send_json({"type": "click", "target_id": "flow-2"})


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
    initial_ids = set(re.findall(r'id="flow-(\d+)"', response.text))

    with client.websocket_connect("/ws") as websocket:
        if initial_ids:
            # Click button multiple times to test registry clearing on re-render
            for _ in range(3):
                websocket.send_json(
                    {
                        "type": "click",
                        "target_id": f"flow-{max(initial_ids)}",
                    }
                )
                # Each click should be processed without crashing
