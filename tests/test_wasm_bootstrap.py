"""Tests for Wasm bootstrap entry point."""

from unittest.mock import MagicMock

from wtfui.web.wasm.bootstrap import (
    WtfUIApp,
    get_document,
    get_pyodide,
    mount,
)


def test_get_document_returns_none_on_server():
    """get_document returns None when not in browser."""
    # On CPython, there's no js module
    assert get_document() is None


def test_get_pyodide_returns_none_on_server():
    """get_pyodide returns None when not in browser."""
    assert get_pyodide() is None


def test_wtfui_app_can_be_created():
    """WtfUIApp can be instantiated with root element."""
    from wtfui.ui import Div

    root = Div()
    app = WtfUIApp(root)
    assert app.root is root


def test_wtfui_app_mount_uses_dom_renderer():
    """WtfUIApp.mount uses DOMRenderer in browser context."""
    from wtfui.ui import Div

    root = Div()
    app = WtfUIApp(root)

    mock_doc = MagicMock()
    mock_container = MagicMock()
    mock_doc.getElementById.return_value = mock_container

    # Mount with mock document
    app.mount(mock_doc, container_id="wtfui-root")

    # Should have queried for container
    mock_doc.getElementById.assert_called_once_with("wtfui-root")


def test_mount_convenience_function():
    """mount() is a convenience wrapper for WtfUIApp."""
    from wtfui.ui import Div

    root = Div()

    mock_doc = MagicMock()
    mock_container = MagicMock()
    mock_doc.getElementById.return_value = mock_container

    # Should not raise
    mount(root, document=mock_doc)


def test_wtfui_app_registers_elements():
    """WtfUIApp registers elements in registry for event handling."""
    from wtfui.ui import Button, Div

    with Div() as root:
        btn = Button("Test", on_click=lambda: None)

    app = WtfUIApp(root)

    # Registry should have elements
    assert app._registry.get(id(root)) is root
    assert app._registry.get(id(btn)) is btn
