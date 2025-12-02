# src/flow/layout/reactive.py
"""Reactive layout nodes with Signal-bound style properties."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import FlexStyle

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.signal import Signal


@dataclass
class ReactiveLayoutNode:
    """A layout node with Signal-bound style properties.

    Combines static base styles with dynamic Signal-bound properties.
    When any bound Signal changes, the node is marked dirty for re-layout.

    Example:
        width = Signal(100)
        node = ReactiveLayoutNode(
            base_style=FlexStyle(flex_direction=FlexDirection.ROW),
            style_signals={"width": width}
        )

        # Layout recomputes when width changes
        width.value = 200
        assert node.is_dirty()
    """

    base_style: FlexStyle = field(default_factory=FlexStyle)
    style_signals: dict[str, Signal[Any]] = field(default_factory=dict)
    children: list[ReactiveLayoutNode] = field(default_factory=list)
    parent: ReactiveLayoutNode | None = field(default=None, repr=False)
    layout: LayoutResult = field(default_factory=LayoutResult)
    _dirty: bool = field(default=True, repr=False)
    _unsubscribes: list[Callable[[], None]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Subscribe to all signal changes."""
        for signal in self.style_signals.values():
            unsub = signal.subscribe(self._on_signal_change)
            self._unsubscribes.append(unsub)

    def _on_signal_change(self) -> None:
        """Called when any bound signal changes."""
        self.mark_dirty()

    def resolve_style(self) -> FlexStyle:
        """Get current style with Signal values resolved.

        Merges base_style with current values from all style_signals.
        """
        if not self.style_signals:
            return self.base_style

        overrides = {name: signal.value for name, signal in self.style_signals.items()}
        return self.base_style.with_updates(**overrides)

    def mark_dirty(self) -> None:
        """Mark this node and ancestors as needing re-layout."""
        self._dirty = True
        if self.parent is not None:
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        """Check if this node needs layout computation."""
        return self._dirty

    def clear_dirty(self) -> None:
        """Clear the dirty flag after layout computation."""
        self._dirty = False

    def add_child(self, child: ReactiveLayoutNode) -> None:
        """Add a child node to this node."""
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: ReactiveLayoutNode) -> None:
        """Remove a child node from this node."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def dispose(self) -> None:
        """Clean up signal subscriptions.

        Call this when the node is no longer needed to prevent memory leaks.
        """
        for unsub in self._unsubscribes:
            unsub()
        self._unsubscribes.clear()

    def to_layout_node(self) -> LayoutNode:
        """Convert to static LayoutNode for computation.

        Creates a snapshot of the current reactive state as a regular
        LayoutNode tree that can be passed to compute_layout().
        """
        node = LayoutNode(style=self.resolve_style())
        for child in self.children:
            node.add_child(child.to_layout_node())
        return node
