import html
from typing import TYPE_CHECKING, ClassVar

from wtfui.core.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from wtfui.core.element import Element
    from wtfui.core.style import Style
    from wtfui.tui.layout.node import LayoutNode


class HTMLRenderer(Renderer):
    TAG_MAP: ClassVar[dict[str, str]] = {
        "Div": "div",
        "VStack": "div",
        "HStack": "div",
        "Card": "div",
        "Text": "div",  # Block-level for proper vertical stacking
        "Button": "button",
        "Input": "input",
        "Window": "div",
        "Box": "div",
        "Flex": "div",
    }

    # Tags that should default to flex column layout
    FLEX_COLUMN_TAGS: ClassVar[set[str]] = {"Box", "VStack", "Card"}
    # Tags that should default to flex row layout
    FLEX_ROW_TAGS: ClassVar[set[str]] = {"HStack"}

    def render(self, element: Element) -> str:
        from wtfui.tui.builder import RenderTreeBuilder

        node = RenderTreeBuilder().build(element)
        return self.render_node(node)

    def render_with_layout(self, element: Element, layout_node: LayoutNode) -> str:
        from wtfui.tui.builder import RenderTreeBuilder

        node = RenderTreeBuilder().build_with_layout(element, layout_node)
        return self.render_node(node)

    # Layout props that should become CSS, not HTML attributes
    LAYOUT_PROPS: ClassVar[dict[str, str]] = {
        "flex_direction": "flex-direction",
        "flex_wrap": "flex-wrap",
        "justify_content": "justify-content",
        "align_items": "align-items",
        "align_content": "align-content",
        "gap": "gap",
        "flex_grow": "flex-grow",
        "flex_shrink": "flex-shrink",
        "flex_basis": "flex-basis",
        "width": "width",
        "height": "height",
        "min_width": "min-width",
        "min_height": "min-height",
        "max_width": "max-width",
        "max_height": "max-height",
        "padding": "padding",
        "margin": "margin",
    }

    # Props that need px units when numeric
    PX_PROPS: ClassVar[set[str]] = {
        "gap",
        "width",
        "height",
        "min_width",
        "min_height",
        "max_width",
        "max_height",
        "padding",
        "margin",
    }

    def render_node(self, node: RenderNode) -> str:
        html_tag = self.TAG_MAP.get(node.tag, "div")

        attrs_parts: list[str] = []
        attrs_parts.append(f'id="wtfui-{node.element_id}"')

        style_parts: list[str] = []
        has_flex_props = False

        # Apply default flex layout for container components
        if node.tag in self.FLEX_COLUMN_TAGS:
            style_parts.append("display: flex")
            style_parts.append("flex-direction: column")
            has_flex_props = True
        elif node.tag in self.FLEX_ROW_TAGS:
            style_parts.append("display: flex")
            style_parts.append("flex-direction: row")
            has_flex_props = True

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
            elif key in self.LAYOUT_PROPS:
                # Convert layout props to CSS
                css_prop = self.LAYOUT_PROPS[key]
                if value is not None:
                    if key in self.PX_PROPS and isinstance(value, int | float):
                        css_value = f"{value}px"
                    else:
                        css_value = str(value)
                    style_parts.append(f"{css_prop}: {css_value}")
                    # Track if we have flex-related props
                    if key in (
                        "flex_direction",
                        "flex_wrap",
                        "justify_content",
                        "align_items",
                        "gap",
                    ):
                        has_flex_props = True
            elif isinstance(value, bool):
                if value:
                    attrs_parts.append(key)
            elif value is not None:
                escaped_value = html.escape(str(value), quote=True)
                attrs_parts.append(f'{key}="{escaped_value}"')

        # Add display: flex if we have flex properties (and not already added)
        if has_flex_props and "display: flex" not in style_parts:
            style_parts.insert(0, "display: flex")

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

    def _style_dict_to_css(self, style: dict[str, object]) -> str:
        from wtfui.core.style import Style

        # Handle _wtfui_style containing a Style object
        if "_wtfui_style" in style:
            wtfui_style = style["_wtfui_style"]
            if isinstance(wtfui_style, Style):
                return self._style_to_css(wtfui_style)

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

    def _style_to_css(self, style: Style) -> str:
        """Convert a Style object to CSS string."""
        parts: list[str] = []

        # Font size mapping
        font_sizes = {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
        }

        # Border radius mapping
        radius_map = {
            "sm": "0.125rem",
            "md": "0.375rem",
            "lg": "0.5rem",
            "xl": "0.75rem",
            "2xl": "1rem",
            "full": "9999px",
        }

        # Shadow mapping
        shadow_map = {
            "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
            "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
            "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        }

        # Color conversion helper
        def color_to_css(color: str) -> str:
            # Tailwind-style colors like "slate-500" need to be converted to CSS
            color_map = {
                "slate-50": "#f8fafc",
                "slate-100": "#f1f5f9",
                "slate-200": "#e2e8f0",
                "slate-300": "#cbd5e1",
                "slate-400": "#94a3b8",
                "slate-500": "#64748b",
                "slate-600": "#475569",
                "slate-700": "#334155",
                "slate-800": "#1e293b",
                "slate-900": "#0f172a",
                "slate-950": "#020617",
                "red-50": "#fef2f2",
                "red-100": "#fee2e2",
                "red-500": "#ef4444",
                "green-50": "#f0fdf4",
                "green-500": "#22c55e",
                "emerald-50": "#ecfdf5",
                "emerald-500": "#10b981",
                "blue-50": "#eff6ff",
                "blue-500": "#3b82f6",
                "blue-600": "#2563eb",
                "white": "#ffffff",
                "black": "#000000",
            }
            return color_map.get(color, color)

        # Background
        if style.bg:
            parts.append(f"background-color: {color_to_css(style.bg)}")

        # Text color
        if style.color:
            parts.append(f"color: {color_to_css(style.color)}")

        # Font
        if style.font_weight:
            parts.append(f"font-weight: {style.font_weight}")
        if style.font_size:
            size = font_sizes.get(style.font_size, style.font_size)
            parts.append(f"font-size: {size}")
        if style.text_align:
            parts.append(f"text-align: {style.text_align}")
        if style.text_decoration:
            parts.append(f"text-decoration: {style.text_decoration}")

        # Opacity
        if style.opacity is not None:
            parts.append(f"opacity: {style.opacity}")

        # Sizing
        if style.w is not None:
            w = f"{style.w}px" if isinstance(style.w, int) else style.w
            parts.append(f"width: {w}")
        if style.h is not None:
            h = f"{style.h}px" if isinstance(style.h, int) else style.h
            parts.append(f"height: {h}")
        if style.w_full:
            parts.append("width: 100%")

        # Padding
        if style.p is not None:
            parts.append(f"padding: {style.p}px")
        if style.px is not None:
            parts.append(f"padding-left: {style.px}px")
            parts.append(f"padding-right: {style.px}px")
        if style.py is not None:
            parts.append(f"padding-top: {style.py}px")
            parts.append(f"padding-bottom: {style.py}px")
        if style.pt is not None:
            parts.append(f"padding-top: {style.pt}px")
        if style.pb is not None:
            parts.append(f"padding-bottom: {style.pb}px")
        if style.pl is not None:
            parts.append(f"padding-left: {style.pl}px")
        if style.pr is not None:
            parts.append(f"padding-right: {style.pr}px")

        # Margin
        if style.m is not None:
            parts.append(f"margin: {style.m}px")
        if style.mt is not None:
            parts.append(f"margin-top: {style.mt}px")
        if style.mb is not None:
            parts.append(f"margin-bottom: {style.mb}px")
        if style.ml is not None:
            parts.append(f"margin-left: {style.ml}px")
        if style.mr is not None:
            parts.append(f"margin-right: {style.mr}px")

        # Flexbox
        if style.flex_grow is not None:
            parts.append(f"flex-grow: {style.flex_grow}")
        if style.flex_shrink is not None:
            parts.append(f"flex-shrink: {style.flex_shrink}")
        if style.align:
            parts.append(f"align-items: {style.align}")
        if style.justify:
            parts.append(f"justify-content: {style.justify}")
        if style.gap is not None:
            parts.append(f"gap: {style.gap}px")
        if style.direction:
            parts.append(f"flex-direction: {style.direction}")

        # Overflow
        if style.overflow:
            parts.append(f"overflow: {style.overflow}")

        # Borders
        border_color = color_to_css(style.border_color) if style.border_color else "#e2e8f0"
        if style.border:
            parts.append(f"border: 1px solid {border_color}")
        else:
            if style.border_top:
                parts.append(f"border-top: 1px solid {border_color}")
            if style.border_bottom:
                parts.append(f"border-bottom: 1px solid {border_color}")
            if style.border_left:
                parts.append(f"border-left: 1px solid {border_color}")
            if style.border_right:
                parts.append(f"border-right: 1px solid {border_color}")

        # Border radius
        if style.rounded:
            radius = radius_map.get(style.rounded, style.rounded)
            parts.append(f"border-radius: {radius}")

        # Shadow
        if style.shadow:
            shadow = shadow_map.get(style.shadow, style.shadow)
            parts.append(f"box-shadow: {shadow}")

        return "; ".join(parts)
