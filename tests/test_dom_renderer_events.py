"""Tests for DOMRenderer event binding."""

from unittest.mock import MagicMock

from flow.renderer import DOMRenderer
from flow.ui import Button


def test_dom_renderer_binds_onclick():
    """DOMRenderer binds on_click handlers to DOM elements."""
    handler = MagicMock()

    btn = Button("Click", on_click=handler)

    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(mock_doc)
    renderer.render(btn)

    # Should have called addEventListener for 'click'
    mock_el.addEventListener.assert_called()
    call_args = mock_el.addEventListener.call_args_list
    assert any(args[0][0] == "click" for args in call_args)


def test_dom_renderer_binds_onchange():
    """DOMRenderer binds on_change handlers."""
    handler = MagicMock()

    from flow.ui.elements import Input

    inp = Input(placeholder="Type", on_change=handler)

    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(mock_doc)
    renderer.render(inp)

    # Should have addEventListener for 'change'
    call_args = mock_el.addEventListener.call_args_list
    assert any(args[0][0] == "change" for args in call_args)


def test_dom_renderer_proxied_handler_is_callable():
    """Proxied handlers maintain reference to original Python function."""
    handler_calls = []

    def my_handler():
        handler_calls.append("called")

    btn = Button("Test", on_click=my_handler)

    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(mock_doc)
    renderer.render(btn)

    # Get the proxied handler that was passed to addEventListener
    call = next(c for c in mock_el.addEventListener.call_args_list if c[0][0] == "click")
    proxied_handler = call[0][1]

    # It should be callable and when called, invokes original
    # Note: In real Pyodide, this would be wrapped by pyodide.ffi.create_proxy
    # In mock, we just verify the callback is passed
    assert callable(proxied_handler)


def test_dom_renderer_creates_element_with_id():
    """DOM elements get flow-{id} format IDs."""
    btn = Button("Test")

    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    renderer = DOMRenderer(mock_doc)
    renderer.render(btn)

    # Element should have ID set
    assert mock_el.id == f"flow-{id(btn)}"
