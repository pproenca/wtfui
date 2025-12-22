import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import FlexStyle

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.signal import Signal


@dataclass
class ReactiveLayoutNode:
    base_style: FlexStyle = field(default_factory=FlexStyle)
    style_signals: dict[str, Signal[Any]] = field(default_factory=dict)
    children: list[ReactiveLayoutNode] = field(default_factory=list)
    parent: ReactiveLayoutNode | None = field(default=None, repr=False)
    layout: LayoutResult = field(default_factory=LayoutResult)
    _dirty: bool = field(default=True, repr=False)
    _unsubscribes: list[Callable[[], None]] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        for signal in self.style_signals.values():
            unsub = signal.subscribe(self._on_signal_change)
            self._unsubscribes.append(unsub)

    def _on_signal_change(self) -> None:
        self.mark_dirty()

    def resolve_style(self) -> FlexStyle:
        if not self.style_signals:
            return self.base_style

        from wtfui.tui.layout.types import parse_dimension, parse_spacing

        dimension_props = {
            "width",
            "height",
            "min_width",
            "min_height",
            "max_width",
            "max_height",
            "flex_basis",
        }

        overrides: dict[str, Any] = {}
        for name, signal in self.style_signals.items():
            value = signal.value
            if name in dimension_props:
                overrides[name] = parse_dimension(value)
            elif name == "padding" or name == "margin":
                overrides[name] = parse_spacing(value)
            else:
                overrides[name] = value

        return self.base_style.with_updates(**overrides)

    def mark_dirty(self) -> None:
        with self._lock:
            self._dirty = True
            parent = self.parent
        if parent is not None:
            parent.mark_dirty()

    def is_dirty(self) -> bool:
        with self._lock:
            return self._dirty

    def clear_dirty(self) -> None:
        with self._lock:
            self._dirty = False

    def clear_dirty_recursive(self) -> None:
        with self._lock:
            self._dirty = False
        for child in self.children:
            child.clear_dirty_recursive()

    def add_child(self, child: ReactiveLayoutNode) -> None:
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: ReactiveLayoutNode) -> None:
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def dispose(self) -> None:
        for unsub in self._unsubscribes:
            unsub()
        self._unsubscribes.clear()

    def to_layout_node(self) -> LayoutNode:
        node = LayoutNode(style=self.resolve_style())
        for child in self.children:
            node.add_child(child.to_layout_node())
        return node
