import html
from typing import TYPE_CHECKING, ClassVar

from wtfui.core.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from wtfui.core.element import Element
    from wtfui.tui.layout.node import LayoutNode


class HTMLRenderer(Renderer):
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
        from wtfui.tui.builder import RenderTreeBuilder

        node = RenderTreeBuilder().build(element)
        return self.render_node(node)

    def render_with_layout(self, element: Element, layout_node: LayoutNode) -> str:
        from wtfui.tui.builder import RenderTreeBuilder

        node = RenderTreeBuilder().build_with_layout(element, layout_node)
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> str:
        html_tag = self.TAG_MAP.get(node.tag, "div")

        attrs_parts: list[str] = []
        attrs_parts.append(f'id="wtfui-{node.element_id}"')

        style_parts: list[str] = []

        if node.layout is not None:
            style_parts.append("position: absolute")
            style_parts.append(f"top: {int(node.layout.y)}px")
            style_parts.append(f"left: {int(node.layout.x)}px")
            style_parts.append(f"width: {int(node.layout.width)}px")
            style_parts.append(f"height: {int(node.layout.height)}px")

        for key, value in node.props.items():
            if key == "cls":
                attrs_parts.append(f'class="{value}"')
            elif key == "style" and isinstance(value, dict):
                css_str = self._style_dict_to_css(value)
                if css_str:
                    style_parts.append(css_str)
            elif key.startswith("on_"):
                continue
            elif isinstance(value, bool):
                if value:
                    attrs_parts.append(key)
            elif value is not None:
                escaped_value = html.escape(str(value), quote=True)
                attrs_parts.append(f'{key}="{escaped_value}"')

        if style_parts:
            attrs_parts.append(f'style="{"; ".join(style_parts)}"')

        attrs_str = " ".join(attrs_parts)

        inner_html = self._render_inner(node)

        if html_tag in ("input", "img", "br", "hr"):
            return f"<{html_tag} {attrs_str} />"

        return f"<{html_tag} {attrs_str}>{inner_html}</{html_tag}>"

    def _render_inner(self, node: RenderNode) -> str:
        if node.text_content:
            return self.render_text(node.text_content)

        if node.label:
            return self.render_text(node.label)

        return "".join(self.render_node(child) for child in node.children)

    def render_text(self, content: str) -> str:
        return html.escape(content, quote=True)

    def _style_dict_to_css(self, style: dict[str, str]) -> str:
        def to_kebab(s: str) -> str:
            result = []
            for i, c in enumerate(s):
                if c.isupper() and i > 0:
                    result.append("-")
                    result.append(c.lower())
                else:
                    result.append(c)
            return "".join(result)

        parts = [f"{to_kebab(k)}: {v}" for k, v in style.items()]
        return "; ".join(parts)
