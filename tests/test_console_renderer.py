# tests/test_console_renderer.py
"""Tests for ConsoleRenderer - the main console rendering class."""

from flow.renderer.console.renderer import ConsoleRenderer
from flow.renderer.protocol import Renderer
from flow.ui import Div


def test_console_renderer_implements_protocol():
    """ConsoleRenderer implements the Renderer ABC."""
    renderer = ConsoleRenderer(width=80, height=24)
    assert isinstance(renderer, Renderer)


def test_console_renderer_has_buffers():
    """ConsoleRenderer maintains front and back buffers."""
    renderer = ConsoleRenderer(width=80, height=24)
    assert renderer.front_buffer is not None
    assert renderer.back_buffer is not None
    assert renderer.front_buffer.width == 80
    assert renderer.back_buffer.height == 24


def test_console_renderer_render_node():
    """ConsoleRenderer can render a RenderNode to buffer."""
    renderer = ConsoleRenderer(width=80, height=24)
    div = Div(cls="container")
    node = div.to_render_node()

    # Should not raise
    renderer.render_node(node)


def test_console_renderer_render_text():
    """ConsoleRenderer writes text to buffer."""
    renderer = ConsoleRenderer(width=80, height=24)
    renderer.render_text_at(0, 0, "Hello")

    assert renderer.back_buffer.get(0, 0).char == "H"
    assert renderer.back_buffer.get(4, 0).char == "o"


def test_console_renderer_flush_produces_diff():
    """flush() generates ANSI output from buffer diff."""
    renderer = ConsoleRenderer(width=80, height=24)
    renderer.render_text_at(0, 0, "Test")

    output = renderer.flush()

    assert "Test" in output


def test_console_renderer_swap_buffers():
    """After flush, front buffer reflects changes."""
    renderer = ConsoleRenderer(width=80, height=24)
    renderer.render_text_at(5, 5, "X")
    renderer.flush()

    # After flush, front should match back
    assert renderer.front_buffer.get(5, 5).char == "X"


def test_console_renderer_clear():
    """clear() resets back buffer."""
    renderer = ConsoleRenderer(width=80, height=24)
    renderer.render_text_at(0, 0, "Data")
    renderer.clear()

    assert renderer.back_buffer.get(0, 0).char == " "
