"""Virtual DOM node for reconciliation."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wtfui.core.element import Element


@dataclass(slots=True)
class VNode:
    """Virtual DOM node snapshot for diffing.

    Captures element state at a point in time for comparison
    during reconciliation.
    """

    key: str
    tag: str
    props: dict[str, Any]
    children: list[VNode] = field(default_factory=list)
    element: Element | None = None

    @classmethod
    def from_element(cls, element: Element) -> VNode:
        """Create VNode tree from Element tree.

        Args:
            element: Root element to snapshot.

        Returns:
            VNode tree mirroring the element structure.
        """
        # Use explicit key or fall back to internal key
        key = element.key if element.key is not None else element._internal_key

        # Copy props, excluding internal attributes
        props = dict(element.props)

        # For Text elements, capture content
        if hasattr(element, "content"):
            props["content"] = element.content

        # Recursively build children
        children = [cls.from_element(child) for child in element.children]

        return cls(
            key=key,
            tag=element.tag,
            props=props,
            children=children,
            element=element,
        )
