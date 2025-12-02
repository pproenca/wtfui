# src/flow/renderer/protocol.py
"""Renderer Protocol - Abstract interface for rendering Elements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flow.element import Element


@dataclass
class RenderNode:
    """
    Abstract representation of an Element for rendering.

    This decouples Elements from their rendering strategy,
    enabling the Universal Runtime (SSR + Wasm).
    """

    tag: str
    element_id: int
    props: dict[str, Any] = field(default_factory=dict)
    children: list[RenderNode] = field(default_factory=list)

    # Special content fields
    text_content: str | None = None
    label: str | None = None


class Renderer(ABC):
    """
    Abstract base class for all renderers.

    Implementations:
    - HTMLRenderer: Outputs HTML strings (Server)
    - DOMRenderer: Outputs js.document calls (Wasm)
    """

    @abstractmethod
    def render(self, element: Element) -> Any:
        """Render an element tree. Return type depends on implementation."""
        ...

    @abstractmethod
    def render_node(self, node: RenderNode) -> Any:
        """Render a single RenderNode."""
        ...

    @abstractmethod
    def render_text(self, content: str) -> Any:
        """Render text content."""
        ...
