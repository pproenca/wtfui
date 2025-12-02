# src/flow/renderer/html.py
"""HTMLRenderer - Renders Elements to HTML strings for SSR."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from flow.element import Element


class HTMLRenderer(Renderer):
    """
    Renders Element trees to HTML strings.

    Used for Server-Side Rendering (SSR).
    Can be swapped with DOMRenderer for Wasm.
    """

    # Tag mapping from Flow element names to HTML tags
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

    def render(self, element: Element) -> str:
        """Render an element tree to HTML."""
        node = element.to_render_node()
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> str:
        """Render a RenderNode to HTML."""
        html_tag = self.TAG_MAP.get(node.tag, "div")

        # Build attributes
        attrs_parts: list[str] = []
        attrs_parts.append(f'id="flow-{node.element_id}"')

        for key, value in node.props.items():
            if key == "cls":
                attrs_parts.append(f'class="{value}"')
            elif key.startswith("on_"):
                # Event handlers are managed client-side
                continue
            elif isinstance(value, bool):
                if value:
                    attrs_parts.append(key)
            elif value is not None:
                attrs_parts.append(f'{key}="{value}"')

        attrs_str = " ".join(attrs_parts)

        # Get inner content
        inner_html = self._render_inner(node)

        # Self-closing tags
        if html_tag in ("input", "img", "br", "hr"):
            return f"<{html_tag} {attrs_str} />"

        return f"<{html_tag} {attrs_str}>{inner_html}</{html_tag}>"

    def _render_inner(self, node: RenderNode) -> str:
        """Render inner content of a node."""
        # Text content takes priority
        if node.text_content:
            return self.render_text(node.text_content)

        # Button labels
        if node.label:
            return self.render_text(node.label)

        # Render children
        return "".join(self.render_node(child) for child in node.children)

    def render_text(self, content: str) -> str:
        """Render text (with HTML escaping for safety)."""
        # Basic escaping for security
        return content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
