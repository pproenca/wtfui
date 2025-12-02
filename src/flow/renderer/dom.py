# src/flow/renderer/dom.py
"""DOMRenderer - Renders Elements directly to browser DOM (for Wasm)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from flow.element import Element


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

    def __init__(self, document: Any) -> None:
        """Initialize with a document object (js.document in Wasm)."""
        self.document = document

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

        # Set attributes
        for key, value in node.props.items():
            if key == "cls":
                el.className = value
            elif key.startswith("on_"):
                # Event handlers would be proxied here
                pass
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
