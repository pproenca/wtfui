# tests/test_dom_renderer.py
"""Tests for DOMRenderer - Placeholder for Wasm support."""

from unittest.mock import MagicMock

from flow.renderer import Renderer
from flow.renderer.dom import DOMRenderer
from flow.ui import Div


def test_dom_renderer_is_renderer():
    """DOMRenderer implements Renderer protocol."""
    renderer = DOMRenderer(document=MagicMock())
    assert isinstance(renderer, Renderer)


def test_dom_renderer_creates_element():
    """DOMRenderer calls document.createElement."""
    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(document=mock_doc)
    div = Div(cls="test")

    renderer.render(div)

    mock_doc.createElement.assert_called_with("div")
