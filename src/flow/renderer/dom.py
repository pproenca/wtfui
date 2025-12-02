# src/flow/renderer/dom.py
"""DOMRenderer - Renders Elements directly to browser DOM (for Wasm)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.element import Element

# Map of Python event prop names to DOM event names
EVENT_MAP: dict[str, str] = {
    "on_click": "click",
    "on_change": "change",
    "on_input": "input",
    "on_submit": "submit",
    "on_focus": "focus",
    "on_blur": "blur",
    "on_keydown": "keydown",
    "on_keyup": "keyup",
    "on_mouseover": "mouseover",
    "on_mouseout": "mouseout",
}


class DOMRenderer(Renderer):
    """
    Renders Element trees directly to the browser DOM.

    Used in WebAssembly (PyScript/Pyodide) environments.
    Receives a `document` object (either real or mock).
    """

    TAG_MAP: ClassVar[dict[str, str]] = {
        "Div": "div",
        "VStack": "div",
        "HStack": "div",
        "Card": "div",
        "Text": "span",
        "Button": "button",
        "Input": "input",
        "Window": "div",
    }

    def __init__(self, document: Any, proxy_factory: Callable[..., Any] | None = None) -> None:
        """Initialize with a document object (js.document in Wasm).

        Args:
            document: The DOM document object (js.document in Pyodide)
            proxy_factory: Function to wrap Python callables for JS (pyodide.ffi.create_proxy)
        """
        self.document = document
        self._proxy_factory = proxy_factory or (lambda x: x)  # Identity if no proxy needed

    def render(self, element: Element) -> Any:
        """Render an element tree to DOM nodes."""
        node = element.to_render_node()
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> Any:
        """Render a RenderNode to a DOM element."""
        html_tag = self.TAG_MAP.get(node.tag, "div")

        # Create the element
        el = self.document.createElement(html_tag)
        el.id = f"flow-{node.element_id}"

        # Set attributes and bind events
        for key, value in node.props.items():
            if key == "cls":
                el.className = value
            elif key in EVENT_MAP:
                # Bind event handler
                self._bind_event(el, key, value)
            elif isinstance(value, bool):
                if value:
                    el.setAttribute(key, "")
            elif value is not None:
                el.setAttribute(key, str(value))

        # Set inner content
        if node.text_content:
            el.textContent = node.text_content
        elif node.label:
            el.textContent = node.label
        else:
            for child in node.children:
                child_el = self.render_node(child)
                el.appendChild(child_el)

        return el

    def render_text(self, content: str) -> Any:
        """Create a text node."""
        return self.document.createTextNode(content)

    def _bind_event(self, el: Any, prop_name: str, handler: Callable[..., Any]) -> None:
        """Bind Python event handler to DOM element.

        Args:
            el: The DOM element
            prop_name: Python prop name (e.g., 'on_click')
            handler: Python callback function

        In Pyodide, the handler must be wrapped with create_proxy()
        to prevent garbage collection and enable JS->Python calls.
        """
        dom_event = EVENT_MAP.get(prop_name)
        if dom_event is None:
            return

        # Wrap handler with proxy for JS interop
        # In tests, proxy_factory is identity; in Pyodide, it's create_proxy
        proxied = self._proxy_factory(handler)
        el.addEventListener(dom_event, proxied)
