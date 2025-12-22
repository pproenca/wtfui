from typing import TYPE_CHECKING

from wtfui.tui.layout.node import LayoutNode
from wtfui.tui.layout.reactive import ReactiveLayoutNode
from wtfui.tui.layout.style import (
    AlignContent,
    AlignItems,
    FlexDirection,
    FlexStyle,
    FlexWrap,
    JustifyContent,
)
from wtfui.tui.layout.types import Dimension, Spacing, parse_dimension, parse_spacing

if TYPE_CHECKING:
    from wtfui.core.element import Element


class LayoutAdapter:
    def to_layout_node(
        self, element: Element, cache: dict[int, LayoutNode] | None = None
    ) -> LayoutNode:
        element_id = id(element)
        if cache is not None and element_id in cache:
            return cache[element_id]

        style = self._extract_flex_style(element)
        node = LayoutNode(style=style)

        for child in element.children:
            node.add_child(self.to_layout_node(child, cache))

        if cache is not None:
            cache[element_id] = node

        return node

    def get_layout_style(self, element: Element) -> FlexStyle:
        return self._extract_flex_style(element)

    def _extract_flex_style(self, element: Element) -> FlexStyle:
        from wtfui.core.style import Style

        props = element.props

        style_obj: Style | None = None
        if "style" in props and isinstance(props["style"], Style):
            style_obj = props["style"]

        def get_prop(prop_name: str, style_attr: str | None = None):
            if prop_name in props:
                return props[prop_name]
            if style_obj is not None and style_attr:
                val = getattr(style_obj, style_attr, None)
                if val is not None:
                    return val
            return None

        width = parse_dimension(get_prop("width", "w"))
        height = parse_dimension(get_prop("height", "h"))
        min_width = parse_dimension(get_prop("min_width"))
        min_height = parse_dimension(get_prop("min_height"))
        max_width = parse_dimension(get_prop("max_width"))
        max_height = parse_dimension(get_prop("max_height"))
        flex_basis = parse_dimension(get_prop("flex_basis"))

        flex_direction = FlexDirection.ROW
        direction_val = get_prop("flex_direction", "direction")
        if direction_val is not None:
            flex_direction = FlexDirection(direction_val)

        flex_wrap = FlexWrap.NO_WRAP
        if "flex_wrap" in props:
            flex_wrap = FlexWrap(props["flex_wrap"])

        justify_content = JustifyContent.FLEX_START
        justify_val = get_prop("justify_content", "justify")
        if justify_val is not None:
            justify_content = JustifyContent(justify_val)

        align_items = AlignItems.STRETCH
        align_val = get_prop("align_items", "align")
        if align_val is not None:
            align_items = AlignItems(align_val)

        align_content = AlignContent.STRETCH
        if "align_content" in props:
            align_content = AlignContent(props["align_content"])

        flex_grow = float(get_prop("flex_grow", "flex_grow") or 0.0)
        flex_shrink = float(get_prop("flex_shrink", "flex_shrink") or 1.0)

        gap = float(get_prop("gap", "gap") or 0.0)
        row_gap = props.get("row_gap")
        column_gap = props.get("column_gap")

        padding = parse_spacing(props.get("padding"))
        margin = parse_spacing(props.get("margin"))

        if style_obj is not None and props.get("padding") is None:
            p_all = style_obj.p or 0
            px = style_obj.px or 0
            py = style_obj.py or 0
            pt = style_obj.pt if style_obj.pt is not None else (py or p_all)
            pb = style_obj.pb if style_obj.pb is not None else (py or p_all)
            pl = style_obj.pl if style_obj.pl is not None else (px or p_all)
            pr = style_obj.pr if style_obj.pr is not None else (px or p_all)
            if any([pt, pb, pl, pr]):
                padding = Spacing(
                    top=Dimension.points(pt),
                    bottom=Dimension.points(pb),
                    left=Dimension.points(pl),
                    right=Dimension.points(pr),
                )

        if style_obj is not None and props.get("margin") is None:
            m_all = style_obj.m or 0
            mt = style_obj.mt if style_obj.mt is not None else m_all
            mb = style_obj.mb if style_obj.mb is not None else m_all
            ml = style_obj.ml if style_obj.ml is not None else m_all
            mr = style_obj.mr if style_obj.mr is not None else m_all
            if any([mt, mb, ml, mr]):
                margin = Spacing(
                    top=Dimension.points(mt),
                    bottom=Dimension.points(mb),
                    left=Dimension.points(ml),
                    right=Dimension.points(mr),
                )

        content = getattr(element, "content", None)
        if content is not None:
            if width.value is None:
                width = Dimension.points(len(str(content)))

            if height.value is None:
                height = Dimension.points(1)

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


class ReactiveLayoutAdapter:
    def to_reactive_layout_node(self, element: Element) -> ReactiveLayoutNode:
        from wtfui.core.signal import Signal

        layout_prop_names = {
            "width",
            "height",
            "min_width",
            "min_height",
            "max_width",
            "max_height",
            "flex_grow",
            "flex_shrink",
            "flex_basis",
            "flex_direction",
            "flex_wrap",
            "justify_content",
            "align_items",
            "align_self",
            "align_content",
            "gap",
            "row_gap",
            "column_gap",
            "padding",
            "margin",
            "padding_top",
            "padding_right",
            "padding_bottom",
            "padding_left",
            "margin_top",
            "margin_right",
            "margin_bottom",
            "margin_left",
        }

        dimension_props = {
            "width",
            "height",
            "min_width",
            "min_height",
            "max_width",
            "max_height",
            "flex_basis",
        }

        enum_prop_parsers: dict[str, type] = {
            "flex_direction": FlexDirection,
            "flex_wrap": FlexWrap,
            "justify_content": JustifyContent,
            "align_items": AlignItems,
            "align_self": AlignItems,
            "align_content": AlignContent,
        }

        style_signals: dict[str, Signal] = {}
        static_props: dict[str, object] = {}

        for key, value in element.props.items():
            if key in layout_prop_names:
                if isinstance(value, Signal):
                    style_signals[key] = value
                elif value is not None:
                    if key in dimension_props:
                        static_props[key] = parse_dimension(value)
                    elif key in ("padding", "margin"):
                        static_props[key] = parse_spacing(value)
                    elif key in enum_prop_parsers:
                        enum_cls = enum_prop_parsers[key]
                        static_props[key] = enum_cls(value) if isinstance(value, str) else value
                    else:
                        static_props[key] = value

        base_style = LayoutAdapter().get_layout_style(element)
        if static_props:
            base_style = base_style.with_updates(**static_props)

        node = ReactiveLayoutNode(
            base_style=base_style,
            style_signals=style_signals,
        )

        for child in element.children:
            node.add_child(self.to_reactive_layout_node(child))

        return node
