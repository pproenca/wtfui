# src/flow/element.py
"""Base Element class - the foundation of all UI nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flow.context import get_current_parent, reset_parent, set_current_parent

if TYPE_CHECKING:
    from contextvars import Token

    from flow.renderer.protocol import RenderNode


class Element:
    """The base class for all UI nodes (Div, VStack, Text, etc.)."""

    def __init__(self, **props: Any) -> None:
        self.tag: str = self.__class__.__name__
        self.props: dict[str, Any] = props
        self.children: list[Element] = []
        self.parent: Element | None = None
        self._token: Token[Element | None] | None = None

    def __enter__(self) -> Element:
        # Capture current parent (if any)
        self.parent = get_current_parent()

        # Attach self to parent's children
        if self.parent is not None:
            self.parent.children.append(self)

        # Push self as the new 'Active Parent'
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
