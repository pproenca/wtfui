import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.element import Element


class ElementRegistry:
    def __init__(self) -> None:
        self._elements: dict[int, Element] = {}
        self._lock = threading.Lock()

    def register(self, element: Element) -> None:
        with self._lock:
            self._elements[id(element)] = element

    def register_tree(self, root: Element) -> None:
        with self._lock:
            self._register_recursive(root)

    def _register_recursive(self, element: Element) -> None:
        self._elements[id(element)] = element
        for child in element.children:
            self._register_recursive(child)

    def get(self, element_id: int) -> Element | None:
        with self._lock:
            return self._elements.get(element_id)

    def get_handler(self, element_id: int, event_type: str) -> Callable[..., Any] | None:
        element = self.get(element_id)
        if element is None:
            return None

        prop_name = f"on_{event_type}"
        return element.props.get(prop_name)

    def clear(self) -> None:
        with self._lock:
            self._elements.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._elements)
