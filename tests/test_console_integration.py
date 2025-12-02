# tests/test_console_integration.py
"""Integration tests for ConsoleRenderer with Flow elements."""

from flow.renderer import ConsoleRenderer, HTMLRenderer
from flow.renderer.protocol import Renderer
from flow.ui import Div, Text, VStack
from flow.ui.spinner import Spinner


def test_console_renderer_exported():
    """ConsoleRenderer is exported from flow.renderer."""
    from flow.renderer import ConsoleRenderer

    assert ConsoleRenderer is not None


def test_both_renderers_share_protocol():
    """HTML and Console renderers implement same protocol."""
    html_r = HTMLRenderer()
    console_r = ConsoleRenderer(width=80, height=24)

    assert isinstance(html_r, Renderer)
    assert isinstance(console_r, Renderer)


def test_render_nested_elements():
    """ConsoleRenderer handles nested element trees."""
    renderer = ConsoleRenderer(width=80, height=24)

    # Nested with statements are intentional - this is Flow's DOM hierarchy pattern
    with Div(cls="container") as root:  # noqa: SIM117
        with VStack():
            Text("Line 1")
            Text("Line 2")

    # Should not raise
    output = renderer.render(root)
    assert isinstance(output, str)


def test_render_spinner_component():
    """ConsoleRenderer can render Spinner."""
    renderer = ConsoleRenderer(width=80, height=24)
    spinner = Spinner(cls="text-blue-500")

    node = spinner.to_render_node()
    renderer.render_node(node)

    output = renderer.flush()
    # Output should contain spinner frame
    assert any(frame in output for frame in spinner.frames)


def test_double_buffer_animation():
    """Multiple renders only emit changes."""
    renderer = ConsoleRenderer(width=80, height=24)

    # First frame
    renderer.render_text_at(0, 0, "Frame 1")
    output1 = renderer.flush()

    # Second frame - same position, different text
    renderer.render_text_at(0, 0, "Frame 2")
    output2 = renderer.flush()

    # Both outputs should contain their respective characters
    # (ANSI escape codes may split the text)
    assert "Frame" in output1
    assert "1" in output1
    assert "2" in output2

    # Second frame should only change the "1" to "2"
    # Most of "Frame " is identical so diff should be smaller
    assert len(output2) < len(output1)
