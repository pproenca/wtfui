# src/flow/layout/node.py
"""Layout node and result types for the Flow Layout Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.style import FlexStyle


@dataclass
class LayoutResult:
    """Computed layout position and size.

    Represents the final computed position (x, y) and dimensions (width, height)
    of a layout node after the flexbox algorithm has been applied.
    """

    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def left(self) -> float:
        """Left edge x-coordinate."""
        return self.x

    @property
    def top(self) -> float:
        """Top edge y-coordinate."""
        return self.y

    @property
    def right(self) -> float:
        """Right edge x-coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Bottom edge y-coordinate."""
        return self.y + self.height


@dataclass
class LayoutNode:
    """A node in the layout tree.

    Represents an element that participates in flexbox layout. Contains a style
    definition, references to children, and the computed layout result.

    Layout Boundary (Council Amendment Gamma): A node with explicit width AND
    height is a "Layout Boundary" and can be computed in parallel.
    """

    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    parent: LayoutNode | None = field(default=None, repr=False)

    # Computed layout (set after compute_layout)
    layout: LayoutResult = field(default_factory=LayoutResult)

    # Internal state for layout algorithm
    _dirty: bool = field(default=True, repr=False)

    def add_child(self, child: LayoutNode) -> None:
        """Add a child node to this node."""
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: LayoutNode) -> None:
        """Remove a child node from this node."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def mark_dirty(self) -> None:
        """Mark this node and ancestors as needing layout.

        Dirty propagation ensures that when a node changes, all ancestor
        nodes are also marked for re-layout (unless they are Layout Boundaries).
        """
        self._dirty = True
        if self.parent is not None:
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        """Check if this node needs layout computation."""
        return self._dirty

    def clear_dirty(self) -> None:
        """Clear the dirty flag after layout computation."""
        self._dirty = False

    def is_layout_boundary(self) -> bool:
        """Check if this node is a Layout Boundary.

        A Layout Boundary has explicit width AND height, meaning its layout
        does not depend on its content and can be computed in parallel.
        """
        return self.style.width.is_defined() and self.style.height.is_defined()
