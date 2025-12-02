"""Tests for LiveSession event handling."""

from unittest.mock import AsyncMock

import pytest

from flow.server.session import LiveSession
from flow.signal import Signal
from flow.ui import Button, Div


@pytest.mark.asyncio
async def test_session_routes_click_events():
    """LiveSession routes click events to element handlers."""
    handler_called = []

    with Div() as root:  # noqa: SIM117 - nested with is intentional for DOM hierarchy
        with Button(
            "Click me",
            on_click=lambda: handler_called.append("clicked"),
        ) as btn:
            pass

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    # Simulate browser sending click event
    event_data = {
        "type": "click",
        "target_id": f"flow-{id(btn)}",
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
        "target_id": "flow-99999999",
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
        "target_id": f"flow-{id(root)}",
    }

    # Should not raise
    await session._handle_event(event_data)


@pytest.mark.asyncio
async def test_session_queues_update_after_handler():
    """Handler execution can trigger update queue."""
    count = Signal(0)

    def increment():
        count.value += 1

    with Div() as root:  # noqa: SIM117 - nested with is intentional for DOM hierarchy
        with Button("Inc", on_click=increment) as btn:
            pass

    mock_ws = AsyncMock()
    session = LiveSession(root, mock_ws)

    event_data = {
        "type": "click",
        "target_id": f"flow-{id(btn)}",
    }

    await session._handle_event(event_data)

    assert count.value == 1
