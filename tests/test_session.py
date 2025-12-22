# tests/test_session.py
"""Tests for LiveSession - WebSocket-based live rendering manager."""

import asyncio
from unittest.mock import AsyncMock

from wtfui.ui import Div, Text
from wtfui.web.renderer import HTMLRenderer
from wtfui.web.server.session import LiveSession


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
        Text("Hello")

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
