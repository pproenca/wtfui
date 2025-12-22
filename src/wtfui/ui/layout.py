from typing import Any, Literal

from wtfui.core.element import Element

DirectionLiteral = Literal["row", "column", "row-reverse", "column-reverse"]
WrapLiteral = Literal["nowrap", "wrap", "wrap-reverse"]
JustifyLiteral = Literal[
    "flex-start", "flex-end", "center", "space-between", "space-around", "space-evenly"
]
AlignLiteral = Literal["flex-start", "flex-end", "center", "stretch", "baseline"]


class Flex(Element):
    __slots__ = ()

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


class Box(Element):
    __slots__ = ()

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
