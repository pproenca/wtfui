# tests/test_renderer_html.py
"""Tests for HTMLRenderer - HTML string rendering with XSS protection."""

from wtfui.core.protocol import RenderNode
from wtfui.web.renderer.html import HTMLRenderer


def test_html_escapes_quotes_in_attributes():
    """Quotes in attributes must be escaped to prevent XSS."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"title": 'He said "hello"', "data-test": "it's fine"},
        children=[],
    )

    html = renderer.render_node(node)

    # Double quotes should be escaped
    assert "&quot;" in html, f"Expected &quot; in: {html}"
    # Single quotes should be escaped
    assert "&#x27;" in html, f"Expected &#x27; in: {html}"


def test_html_escapes_angle_brackets_in_text():
    """Angle brackets in text content must be escaped to prevent XSS."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={},
        children=[],
        text_content="<script>alert('xss')</script>",
    )

    html = renderer.render_node(node)

    # Script tag should be escaped
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_escapes_ampersand_in_text():
    """Ampersands in text content must be escaped."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={},
        children=[],
        text_content="Tom & Jerry",
    )

    html = renderer.render_node(node)

    assert "&amp;" in html
    assert "Tom &amp; Jerry" in html
