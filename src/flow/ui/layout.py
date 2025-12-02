# src/flow/ui/layout.py
"""Layout-oriented UI elements: Flex and Box containers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from flow.element import Element, _parse_dimension, _parse_spacing

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexStyle

DirectionLiteral = Literal["row", "column", "row-reverse", "column-reverse"]
WrapLiteral = Literal["nowrap", "wrap", "wrap-reverse"]
JustifyLiteral = Literal[
    "flex-start", "flex-end", "center", "space-between", "space-around", "space-evenly"
]
AlignLiteral = Literal["flex-start", "flex-end", "center", "stretch", "baseline"]


class Flex(Element):
    """A Flexbox container element.

    Provides a convenient way to create flex containers with typed parameters.
    All layout properties are passed to the underlying FlexStyle.
    Can also be a flex item when nested (supports flex_grow/flex_shrink).
    """

    def __init__(
        self,
        *,
        direction: DirectionLiteral = "row",
        wrap: WrapLiteral = "nowrap",
        justify: JustifyLiteral = "flex-start",
        align: AlignLiteral = "stretch",
        gap: float = 0,
        width: float | str | None = None,
        height: float | str | None = None,
        padding: float | tuple[float, ...] | None = None,
        flex_grow: float = 0,
        flex_shrink: float = 1,
        **props: Any,
    ) -> None:
        # Convert to element props
        super().__init__(
            flex_direction=direction,
            flex_wrap=wrap,
            justify_content=justify,
            align_items=align,
            gap=gap,
            width=width,
            height=height,
            padding=padding,
            flex_grow=flex_grow,
            flex_shrink=flex_shrink,
            **props,
        )
        self._direction = direction
        self._wrap = wrap
        self._justify = justify
        self._align = align
        self._gap = gap
        self._width = width
        self._height = height
        self._padding = padding
        self._flex_grow = flex_grow
        self._flex_shrink = flex_shrink

    def get_layout_style(self) -> FlexStyle:
        """Get the FlexStyle for this Flex container."""
        from flow.layout.style import (
            AlignItems,
            FlexDirection,
            FlexStyle,
            FlexWrap,
            JustifyContent,
        )

        return FlexStyle(
            flex_direction=FlexDirection(self._direction),
            flex_wrap=FlexWrap(self._wrap),
            justify_content=JustifyContent(self._justify),
            align_items=AlignItems(self._align),
            gap=self._gap,
            width=_parse_dimension(self._width),
            height=_parse_dimension(self._height),
            padding=_parse_spacing(self._padding),
            flex_grow=self._flex_grow,
            flex_shrink=self._flex_shrink,
        )

    def to_layout_node(self) -> LayoutNode:
        """Convert this Flex element to a LayoutNode."""
        from flow.layout.node import LayoutNode

        node = LayoutNode(style=self.get_layout_style())
        for child in self.children:
            if hasattr(child, "to_layout_node"):
                node.add_child(child.to_layout_node())
        return node


class Box(Element):
    """A box element with layout properties.

    A simple container that can have fixed dimensions or flex properties.
    Used as a child within Flex containers.
    """

    def __init__(
        self,
        *,
        width: float | str | None = None,
        height: float | str | None = None,
        flex_grow: float = 0,
        flex_shrink: float = 1,
        flex_basis: float | str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(
            width=width,
            height=height,
            flex_grow=flex_grow,
            flex_shrink=flex_shrink,
            flex_basis=flex_basis,
            **props,
        )
        self._width = width
        self._height = height
        self._flex_grow = flex_grow
        self._flex_shrink = flex_shrink
        self._flex_basis = flex_basis

    def get_layout_style(self) -> FlexStyle:
        """Get the FlexStyle for this Box element."""
        from flow.layout.style import FlexStyle

        return FlexStyle(
            width=_parse_dimension(self._width),
            height=_parse_dimension(self._height),
            flex_grow=self._flex_grow,
            flex_shrink=self._flex_shrink,
            flex_basis=_parse_dimension(self._flex_basis),
        )

    def to_layout_node(self) -> LayoutNode:
        """Convert this Box element to a LayoutNode."""
        from flow.layout.node import LayoutNode

        node = LayoutNode(style=self.get_layout_style())
        for child in self.children:
            if hasattr(child, "to_layout_node"):
                node.add_child(child.to_layout_node())
        return node
