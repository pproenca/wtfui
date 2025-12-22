"""Tests for LiveSession event handling."""

from unittest.mock import AsyncMock

import pytest

from wtfui.core.signal import Signal
from wtfui.ui import Button, Div
from wtfui.web.server.session import LiveSession


@pytest.mark.asyncio
async def test_session_routes_click_events():
    """LiveSession routes click events to element handlers."""
    handler_called = []

    with Div() as root:
        btn = Button(
            "Click me",
            on_click=lambda: handler_called.append("clicked"),
        )

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Simulate browser sending click event
    event_data = {
        "type": "click",
        "target_id": f"wtfui-{id(btn)}",
    }

    await session._handle_event(event_data)

    assert handler_called == ["clicked"]


@pytest.mark.asyncio
async def test_session_handles_unknown_element():
    """LiveSession handles events for unknown elements gracefully."""
    root = Div()
    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Event for non-existent element
    event_data = {
        "type": "click",
        "target_id": "wtfui-99999999",
    }

    # Should not raise
    await session._handle_event(event_data)


@pytest.mark.asyncio
async def test_session_handles_element_without_handler():
    """LiveSession handles elements without event handlers."""
    root = Div()  # No on_click handler
    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    event_data = {
        "type": "click",
        "target_id": f"wtfui-{id(root)}",
    }

    # Should not raise
    await session._handle_event(event_data)


@pytest.mark.asyncio
async def test_session_queues_update_after_handler():
    """Handler execution can trigger update queue."""
    count = Signal(0)

    def increment():
        count.value += 1

    with Div() as root:
        btn = Button("Inc", on_click=increment)

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    event_data = {
        "type": "click",
        "target_id": f"wtfui-{id(btn)}",
    }

    await session._handle_event(event_data)

    assert count.value == 1


@pytest.mark.asyncio
async def test_session_passes_value_to_input_handler():
    """LiveSession passes value from input events to handlers."""
    from wtfui.ui import Input

    received_values = []

    def on_input(value: str) -> None:
        received_values.append(value)

    with Div() as root:
        inp = Input(on_input=on_input)

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Simulate browser sending input event with value
    event_data = {
        "type": "input",
        "target_id": f"wtfui-{id(inp)}",
        "value": "hello",
    }

    await session._handle_event(event_data)

    assert received_values == ["hello"]


@pytest.mark.asyncio
async def test_session_passes_value_to_change_handler():
    """LiveSession passes value from change events to handlers."""
    from wtfui.ui import Input

    received_values = []

    def on_change(value: str) -> None:
        received_values.append(value)

    with Div() as root:
        inp = Input(on_change=on_change)

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Simulate browser sending change event with value
    event_data = {
        "type": "change",
        "target_id": f"wtfui-{id(inp)}",
        "value": "world",
    }

    await session._handle_event(event_data)

    assert received_values == ["world"]


@pytest.mark.asyncio
async def test_session_input_updates_bound_signal():
    """Input events update bound signal via on_input handler."""
    from wtfui.ui import Input

    bound_value = Signal("initial")

    with Div() as root:
        inp = Input(bind=bound_value)

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Simulate browser sending input event
    event_data = {
        "type": "input",
        "target_id": f"wtfui-{id(inp)}",
        "value": "updated",
    }

    await session._handle_event(event_data)

    assert bound_value.value == "updated"
