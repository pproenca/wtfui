import warnings
from typing import TYPE_CHECKING, Any, ClassVar

from wtfui.core.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.element import Element


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
        self.document = document

        if proxy_factory is None:
            warnings.warn(
                "DOMRenderer created without proxy_factory. "
                "Event handlers may not work correctly in Pyodide. "
                "Pass create_proxy from pyodide.ffi for proper JS interop.",
                UserWarning,
                stacklevel=2,
            )
            self._proxy_factory = lambda x: x
        else:
            self._proxy_factory = proxy_factory

    def render(self, element: Element) -> Any:
        from wtfui.tui.builder import RenderTreeBuilder

        node = RenderTreeBuilder().build(element)
        return self.render_node(node)

    def render_node(self, node: RenderNode) -> Any:
        html_tag = self.TAG_MAP.get(node.tag, "div")

        el = self.document.createElement(html_tag)
        el.id = f"wtfui-{node.element_id}"

        for key, value in node.props.items():
            if key == "cls":
                el.className = value
            elif key in EVENT_MAP:
                self._bind_event(el, key, value)
            elif isinstance(value, bool):
                if value:
                    el.setAttribute(key, "")
            elif value is not None:
                el.setAttribute(key, str(value))

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
        return self.document.createTextNode(content)

    def _bind_event(self, el: Any, prop_name: str, handler: Callable[..., Any]) -> None:
        dom_event = EVENT_MAP.get(prop_name)
        if dom_event is None:
            return

        proxied = self._proxy_factory(handler)
        el.addEventListener(dom_event, proxied)
