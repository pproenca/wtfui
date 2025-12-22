from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.core.element import Element
    from wtfui.core.protocol import RenderNode
    from wtfui.tui.layout.node import LayoutNode


class RenderTreeBuilder:
    def build(self, element: Element) -> RenderNode:
        from wtfui.core.protocol import RenderNode
        from wtfui.core.style import Style
        from wtfui.tui.layout.style_resolver import resolve_style_conflict

        props = dict(element.props)

        if "class_" in props:
            layout_props = {
                "width": props.get("width"),
                "height": props.get("height"),
                "flex_direction": props.get("flex_direction"),
                "flex_wrap": props.get("flex_wrap"),
                "justify_content": props.get("justify_content"),
                "align_items": props.get("align_items"),
                "gap": props.get("gap"),
                "flex_grow": props.get("flex_grow"),
            }
            props["class_"] = resolve_style_conflict(props["class_"], layout_props)

        if "style" in props and isinstance(props["style"], Style):
            typed_style = props["style"]

            props["style"] = {
                "_wtfui_style": typed_style,
            }

        node = RenderNode(
            tag=element.tag,
            element_id=id(element),
            props=props,
        )

        if hasattr(element, "content") and element.content:
            node.text_content = str(element.content)

        if hasattr(element, "current_frame"):
            node.text_content = str(element.current_frame)

        if hasattr(element, "label") and element.label:
            node.label = str(element.label)

        # Extract text_value for Input elements to render as value attribute
        # This handles both bound (bind=Signal) and unbound (on_change only) inputs
        if hasattr(element, "text_value"):
            node.props["value"] = element.text_value

        node.children = [self.build(child) for child in element.children]

        return node

    def build_with_layout(self, element: Element, layout_node: LayoutNode) -> RenderNode:
        from wtfui.core.protocol import RenderNode
        from wtfui.core.style import Style

        layout = layout_node.layout

        props = dict(element.props)
        existing_style = props.get("style", {})

        if isinstance(existing_style, Style):
            props["style"] = {"_wtfui_style": existing_style}
        elif isinstance(existing_style, dict):
            props["style"] = {
                k: v
                for k, v in existing_style.items()
                if k not in ("position", "top", "left", "width", "height")
            }

        node = RenderNode(
            tag=element.tag,
            element_id=id(element),
            props=props,
            layout=layout,
        )

        if hasattr(element, "content") and element.content:
            node.text_content = str(element.content)

        if hasattr(element, "label") and element.label:
            node.label = str(element.label)

        # Extract text_value for Input elements to render as value attribute
        # This handles both bound (bind=Signal) and unbound (on_change only) inputs
        if hasattr(element, "text_value"):
            node.props["value"] = element.text_value

        for i, child in enumerate(element.children):
            if i < len(layout_node.children):
                child_render = self.build_with_layout(child, layout_node.children[i])
            else:
                child_render = self.build(child)
            node.children.append(child_render)

        return node
