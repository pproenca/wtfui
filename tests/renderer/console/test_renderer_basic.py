# tests/test_console_renderer.py
"""Tests for ConsoleRenderer - the main console rendering class."""

from wtfui.core.protocol import Renderer
from wtfui.tui.renderer.renderer import ConsoleRenderer
from wtfui.ui import Div


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
    from wtfui.tui.builder import RenderTreeBuilder

    renderer = ConsoleRenderer(width=80, height=24)
    div = Div(cls="container")
    node = RenderTreeBuilder().build(div)

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


def test_console_renderer_handles_various_css_units():
    """Console renderer should handle different CSS units gracefully."""
    from wtfui.core.protocol import RenderNode

    renderer = ConsoleRenderer(width=80, height=24)

    # Test with raw numbers (no units)
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"left": "10", "top": "5"}},
        children=[
            RenderNode(
                tag="Text",
                element_id=2,
                props={},
                children=[],
                text_content="Hello",
            )
        ],
    )

    # Should not raise - raw numbers without units
    renderer.render_node_with_layout(node)

    # Verify text was rendered at correct position
    assert renderer.back_buffer.get(10, 5).char == "H"


def test_console_renderer_handles_numeric_style_values():
    """Console renderer should handle numeric values (not just strings)."""
    from wtfui.core.protocol import RenderNode

    renderer = ConsoleRenderer(width=80, height=24)

    # Test with numeric values directly (not strings)
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"left": 15, "top": 3}},
        children=[
            RenderNode(
                tag="Text",
                element_id=2,
                props={},
                children=[],
                text_content="Hi",
            )
        ],
    )

    # Should not raise
    renderer.render_node_with_layout(node)

    # Verify text was rendered at correct position
    assert renderer.back_buffer.get(15, 3).char == "H"
