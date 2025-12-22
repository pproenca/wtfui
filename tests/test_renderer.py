# tests/test_renderer.py
"""Tests for Renderer Protocol - Abstract rendering for Universal Runtime."""

from wtfui.core.protocol import Renderer
from wtfui.ui import Button, Div, Text
from wtfui.web.renderer import HTMLRenderer


def test_renderer_protocol_exists():
    """Renderer is an abstract protocol."""
    assert hasattr(Renderer, "render")
    assert hasattr(Renderer, "render_node")
    assert hasattr(Renderer, "render_text")


def test_element_produces_render_node():
    """Elements produce RenderNode for renderers to consume."""
    from wtfui.tui.builder import RenderTreeBuilder

    div = Div(cls="container")
    node = RenderTreeBuilder().build(div)

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
    assert f'id="wtfui-{id(div)}"' in html


def test_html_renderer_text_element():
    """HTMLRenderer renders Text content."""
    text = Text("Hello, World!")
    renderer = HTMLRenderer()

    html = renderer.render(text)
    assert "Hello, World!" in html


def test_html_renderer_nested_elements():
    """HTMLRenderer handles nested children."""
    with Div(cls="parent") as parent:
        Text("Child 1")
        Text("Child 2")

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
