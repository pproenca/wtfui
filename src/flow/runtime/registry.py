"""Element Registry - Maps element IDs to instances for event routing.

When the client sends an event like {"type": "click", "target_id": "flow-12345"},
the server uses this registry to find the element and call its handler.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.element import Element


class ElementRegistry:
    """
    Thread-safe registry mapping element IDs to instances.

    Used by LiveSession to route client events to handlers.
    """

    def __init__(self) -> None:
        self._elements: dict[int, Element] = {}
        self._lock = threading.Lock()

    def register(self, element: Element) -> None:
        """Register a single element."""
        with self._lock:
            self._elements[id(element)] = element

    def register_tree(self, root: Element) -> None:
        """Register all elements in a tree (recursive)."""
        with self._lock:
            self._register_recursive(root)

    def _register_recursive(self, element: Element) -> None:
        """Recursively register element and children."""
        self._elements[id(element)] = element
        for child in element.children:
            self._register_recursive(child)

    def get(self, element_id: int) -> Element | None:
        """Get an element by its ID."""
        with self._lock:
            return self._elements.get(element_id)

    def get_handler(self, element_id: int, event_type: str) -> Callable[[], Any] | None:
        """Get the event handler for an element.

        Args:
            element_id: The element's Python id()
            event_type: Event type (e.g., "click", "change")

        Returns:
            The handler function, or None if not found
        """
        element = self.get(element_id)
        if element is None:
            return None

        # Map event types to prop names
        prop_name = f"on_{event_type}"
        return element.props.get(prop_name)

    def clear(self) -> None:
        """Clear all registered elements."""
        with self._lock:
            self._elements.clear()

    def __len__(self) -> int:
        """Number of registered elements."""
        with self._lock:
            return len(self._elements)
