# tests/test_dom_renderer.py
"""Tests for DOMRenderer - Placeholder for Wasm support."""

from unittest.mock import MagicMock

from wtfui.core.protocol import Renderer
from wtfui.ui import Div
from wtfui.web.renderer.dom import DOMRenderer


def test_dom_renderer_is_renderer():
    """DOMRenderer implements Renderer protocol."""
    # Provide mock proxy to avoid warning
    renderer = DOMRenderer(document=MagicMock(), proxy_factory=lambda x: x)
    assert isinstance(renderer, Renderer)


def test_dom_renderer_creates_element():
    """DOMRenderer calls document.createElement."""
    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    # Provide mock proxy to avoid warning
    renderer = DOMRenderer(document=mock_doc, proxy_factory=lambda x: x)
    div = Div(cls="test")

    renderer.render(div)

    mock_doc.createElement.assert_called_with("div")


def test_dom_renderer_warns_on_missing_proxy_factory():
    """DOMRenderer should warn if proxy_factory is not provided.

    In Pyodide, event handlers need create_proxy for proper JS interop.
    Missing proxy_factory means event handlers may silently fail.
    """
    import warnings

    mock_doc = MagicMock()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        DOMRenderer(document=mock_doc)  # No proxy_factory

        # Should have one warning about missing proxy
        assert len(w) == 1
        assert "proxy_factory" in str(w[0].message).lower()
        assert issubclass(w[0].category, UserWarning)


def test_dom_renderer_no_warning_with_proxy_factory():
    """DOMRenderer should not warn when proxy_factory is provided."""
    import warnings

    mock_doc = MagicMock()
    mock_proxy = MagicMock(side_effect=lambda x: x)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        DOMRenderer(document=mock_doc, proxy_factory=mock_proxy)

        # Should have no warnings
        assert len(w) == 0
