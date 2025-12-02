"""Wasm Entry Point - Bootstrap Flow apps in browser environment.

This module provides the entry point for running Flow applications
in WebAssembly (Pyodide/Emscripten) environments.

Usage in browser (after Pyodide loads):
    import flow.wasm.bootstrap as flow
    from myapp import App

    flow.mount(App())

Or using the FlowApp class directly:
    app = FlowApp(App())
    app.mount(document)

Per MANIFEST.md Tenet III: "python app.py starts full-stack dev"
In Wasm, this becomes the entry point instead of the server.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from flow.renderer import DOMRenderer
from flow.runtime.registry import ElementRegistry
from flow.wasm.platform import is_browser

if TYPE_CHECKING:
    from flow.element import Element


def get_pyodide() -> Any:
    """Get the pyodide module if running in Pyodide.

    Returns None if not in Pyodide environment.
    """
    return sys.modules.get("pyodide")


def get_document() -> Any:
    """Get the browser document object if in Wasm.

    Returns None if not in browser environment.
    """
    if not is_browser():
        return None

    # In Pyodide, js module provides browser globals
    js = sys.modules.get("js")
    if js is not None:
        return getattr(js, "document", None)

    return None


def _get_proxy_factory() -> Any:
    """Get pyodide.ffi.create_proxy if available.

    This is needed to wrap Python callbacks for JavaScript interop.
    Without this, Python callbacks would be garbage collected.
    """
    pyodide = get_pyodide()
    if pyodide is None:
        return lambda x: x  # Identity function for testing

    ffi = getattr(pyodide, "ffi", None)
    if ffi is not None:
        return getattr(ffi, "create_proxy", lambda x: x)

    return lambda x: x


class FlowApp:
    """
    Main application class for Wasm deployment.

    Wraps a root Element tree and handles:
    - DOM rendering via DOMRenderer
    - Event registration via ElementRegistry
    - Pyodide proxy management for callbacks
    """

    def __init__(self, root: Element) -> None:
        """Create a FlowApp with the given root element.

        Args:
            root: The root Element of your UI tree
        """
        self.root = root
        self._registry = ElementRegistry()
        self._registry.register_tree(root)
        self._renderer: DOMRenderer | None = None

    def mount(
        self,
        document: Any | None = None,
        container_id: str = "flow-root",
    ) -> None:
        """Mount the app to the DOM.

        Args:
            document: The browser document object (auto-detected if None)
            container_id: ID of the container element to mount into
        """
        if document is None:
            document = get_document()

        if document is None:
            msg = "Cannot mount: not in browser environment"
            raise RuntimeError(msg)

        # Create renderer with Pyodide proxy factory
        proxy_factory = _get_proxy_factory()
        self._renderer = DOMRenderer(document, proxy_factory)

        # Render the tree
        dom_tree = self._renderer.render(self.root)

        # Find container and append
        container = document.getElementById(container_id)
        if container is not None:
            # Clear existing content
            container.innerHTML = ""
            container.appendChild(dom_tree)


def mount(
    root: Element,
    document: Any | None = None,
    container_id: str = "flow-root",
) -> FlowApp:
    """Convenience function to mount a Flow app.

    This is the recommended entry point for Wasm apps:

        from flow.wasm.bootstrap import mount
        from myapp import App

        mount(App())

    Args:
        root: The root Element of your UI tree
        document: Browser document (auto-detected if None)
        container_id: ID of container element

    Returns:
        The FlowApp instance (for debugging/inspection)
    """
    app = FlowApp(root)
    app.mount(document, container_id)
    return app
