# src/flow/element.py
"""Base Element class - the foundation of all UI nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flow.context import get_current_parent, reset_parent, set_current_parent

if TYPE_CHECKING:
    from contextvars import Token

    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexStyle
    from flow.layout.types import Dimension, Spacing
    from flow.renderer.protocol import RenderNode


class Element:
    """The base class for all UI nodes (Div, VStack, Text, etc.)."""

    def __init__(self, **props: Any) -> None:
        self.tag: str = self.__class__.__name__
        self.props: dict[str, Any] = props
        self.children: list[Element] = []
        self._token: Token[Element | None] | None = None

        # Auto-Mount: Immediately attach to the active container
        # This allows 'Text("Hi")' to work without a 'with' block
        self.parent = get_current_parent()
        if self.parent is not None:
            self.parent.children.append(self)

    def __enter__(self) -> Element:
        # Context Entry: Only needed if this element HAS children
        # Element is already attached to parent via __init__
        self._token = set_current_parent(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        # Pop self off the stack, restoring the previous parent
        if self._token is not None:
            reset_parent(self._token)
            self._token = None

    def __repr__(self) -> str:
        return f"<{self.tag} children={len(self.children)} />"

    def to_render_node(self) -> RenderNode:
        """
        Convert this element to an abstract RenderNode.

        This decouples Elements from rendering strategy,
        enabling Universal Runtime (SSR + Wasm).
        """
        from flow.renderer.protocol import RenderNode

        node = RenderNode(
            tag=self.tag,
            element_id=id(self),
            props=dict(self.props),
        )

        # Handle text content (Text elements)
        if hasattr(self, "content") and self.content:
            node.text_content = str(self.content)

        # Handle button labels
        if hasattr(self, "label") and self.label:
            node.label = str(self.label)

        # Recursively convert children
        node.children = [child.to_render_node() for child in self.children]

        return node

    def to_render_node_with_layout(self, layout_node: LayoutNode) -> RenderNode:
        """Convert to RenderNode with computed layout positions.

        Takes a LayoutNode (after compute_layout) and merges the computed
        positions and dimensions into the RenderNode's style prop.

        Args:
            layout_node: The corresponding LayoutNode with computed layout.

        Returns:
            RenderNode with layout positions in the style prop.
        """
        from flow.renderer.protocol import RenderNode

        # Get computed layout
        layout = layout_node.layout

        # Build layout style dict (format as int if whole number)
        def fmt(v: float) -> str:
            return f"{int(v)}px" if v == int(v) else f"{v}px"

        layout_style = {
            "position": "absolute",
            "top": fmt(layout.y),
            "left": fmt(layout.x),
            "width": fmt(layout.width),
            "height": fmt(layout.height),
        }

        # Merge with existing props
        props = dict(self.props)
        existing_style = props.get("style", {})
        if isinstance(existing_style, dict):
            layout_style.update(existing_style)
        props["style"] = layout_style

        node = RenderNode(
            tag=self.tag,
            element_id=id(self),
            props=props,
        )

        # Handle text content (Text elements)
        if hasattr(self, "content") and self.content:
            node.text_content = str(self.content)

        # Handle button labels
        if hasattr(self, "label") and self.label:
            node.label = str(self.label)

        # Recursively convert children with their layout
        for i, child in enumerate(self.children):
            if i < len(layout_node.children):
                child_render = child.to_render_node_with_layout(layout_node.children[i])
            else:
                child_render = child.to_render_node()
            node.children.append(child_render)

        return node

    def get_layout_style(self) -> FlexStyle:
        """Convert element props to a FlexStyle for layout computation.

        Parses layout-related props (flex_direction, width, height, etc.)
        and returns a FlexStyle dataclass for use with the layout engine.
        """
        from flow.layout.style import (
            AlignContent,
            AlignItems,
            FlexDirection,
            FlexStyle,
            FlexWrap,
            JustifyContent,
        )

        # Parse dimensions
        width = _parse_dimension(self.props.get("width"))
        height = _parse_dimension(self.props.get("height"))
        min_width = _parse_dimension(self.props.get("min_width"))
        min_height = _parse_dimension(self.props.get("min_height"))
        max_width = _parse_dimension(self.props.get("max_width"))
        max_height = _parse_dimension(self.props.get("max_height"))
        flex_basis = _parse_dimension(self.props.get("flex_basis"))

        # Parse flex container properties
        flex_direction = FlexDirection.ROW
        if "flex_direction" in self.props:
            flex_direction = FlexDirection(self.props["flex_direction"])

        flex_wrap = FlexWrap.NO_WRAP
        if "flex_wrap" in self.props:
            flex_wrap = FlexWrap(self.props["flex_wrap"])

        justify_content = JustifyContent.FLEX_START
        if "justify_content" in self.props:
            justify_content = JustifyContent(self.props["justify_content"])

        align_items = AlignItems.STRETCH
        if "align_items" in self.props:
            align_items = AlignItems(self.props["align_items"])

        align_content = AlignContent.STRETCH
        if "align_content" in self.props:
            align_content = AlignContent(self.props["align_content"])

        # Parse flex item properties
        flex_grow = float(self.props.get("flex_grow", 0.0))
        flex_shrink = float(self.props.get("flex_shrink", 1.0))

        # Parse gap
        gap = float(self.props.get("gap", 0.0))
        row_gap = self.props.get("row_gap")
        column_gap = self.props.get("column_gap")

        # Parse spacing
        padding = _parse_spacing(self.props.get("padding"))
        margin = _parse_spacing(self.props.get("margin"))

        return FlexStyle(
            flex_direction=flex_direction,
            flex_wrap=flex_wrap,
            justify_content=justify_content,
            align_items=align_items,
            align_content=align_content,
            flex_grow=flex_grow,
            flex_shrink=flex_shrink,
            flex_basis=flex_basis,
            width=width,
            height=height,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height,
            gap=gap,
            row_gap=row_gap,
            column_gap=column_gap,
            padding=padding,
            margin=margin,
        )

    def to_layout_node(self) -> LayoutNode:
        """Convert this element to a LayoutNode for layout computation.

        Creates a LayoutNode tree matching the element tree structure,
        allowing layout to be computed independently of rendering.
        """
        from flow.layout.node import LayoutNode

        node = LayoutNode(style=self.get_layout_style())
        for child in self.children:
            node.add_child(child.to_layout_node())
        return node


def _parse_dimension(value: float | str | None) -> Dimension:
    """Parse a dimension value into a Dimension object."""
    from flow.layout.types import Dimension

    if value is None:
        return Dimension.auto()
    if isinstance(value, int | float):
        return Dimension.points(float(value))
    if isinstance(value, str):
        if value.endswith("%"):
            return Dimension.percent(float(value[:-1]))
        return Dimension.points(float(value.replace("px", "")))
    return Dimension.auto()


def _parse_spacing(value: float | tuple[float, ...] | None) -> Spacing:
    """Parse a spacing value into a Spacing object."""
    from flow.layout.types import Dimension, Spacing

    if value is None:
        return Spacing()
    if isinstance(value, int | float):
        d = Dimension.points(float(value))
        return Spacing(top=d, right=d, bottom=d, left=d)
    if isinstance(value, tuple):
        if len(value) == 4:
            return Spacing(
                top=Dimension.points(value[0]),
                right=Dimension.points(value[1]),
                bottom=Dimension.points(value[2]),
                left=Dimension.points(value[3]),
            )
        if len(value) == 2:
            v = Dimension.points(value[0])
            h = Dimension.points(value[1])
            return Spacing(top=v, right=h, bottom=v, left=h)
        if len(value) == 1:
            d = Dimension.points(value[0])
            return Spacing(top=d, right=d, bottom=d, left=d)
    return Spacing()
