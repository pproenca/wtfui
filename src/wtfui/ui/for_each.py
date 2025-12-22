import threading
import weakref
from typing import TYPE_CHECKING, Any

from wtfui.core.context import get_current_runtime
from wtfui.core.effect import Effect
from wtfui.core.element import Element
from wtfui.ui.elements import Div

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.computed import Computed
    from wtfui.core.signal import Signal


class For[T](Element):
    __slots__ = (
        "_disposed",
        "_effect",
        "_initial_sync_done",
        "_items",
        "_lock",
        "_runtime_ref",
        "each",
        "key",
        "render",
    )

    def __init__(
        self,
        each: Signal[list[T]] | Computed[list[T]],
        render: Callable[[T, int], None],
        key: Callable[[T], Any] | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)

        if not hasattr(each, "value") and not callable(each):
            msg = f"each must be Signal or Computed, got {type(each).__name__}"
            raise TypeError(msg)
        if not callable(render):
            msg = f"render must be callable, got {type(render).__name__}"
            raise TypeError(msg)
        if key is not None and not callable(key):
            msg = f"key must be callable, got {type(key).__name__}"
            raise TypeError(msg)

        self.each = each
        self.render = render
        self.key = key or id

        runtime = get_current_runtime()
        self._runtime_ref = weakref.ref(runtime) if runtime is not None else None

        self._items = {}
        self._lock = threading.Lock()
        self._disposed = False
        self._effect = None
        self._initial_sync_done = False

        self._effect = Effect(self._sync)

    def _get_items(self) -> list[T]:
        if callable(self.each):
            return self.each()
        return self.each.value

    def _create_item_container(self, item: T, index: int) -> Element:
        from wtfui.core.context import reset_parent, set_current_parent

        if self._disposed:
            msg = "Cannot create items on disposed For component"
            raise RuntimeError(msg)

        container = Div()

        if container.parent is not None:
            container.parent.children.remove(container)
        container.parent = self

        token = set_current_parent(container)
        try:
            self.render(item, index)
        finally:
            reset_parent(token)

        return container

    def _trigger_runtime_rebuild(self) -> None:
        if self._runtime_ref is None:
            return

        runtime = self._runtime_ref()
        if runtime is not None and hasattr(runtime, "needs_rebuild"):
            runtime.needs_rebuild = True
            runtime.is_dirty = True

    def _sync(self) -> None:
        if self._disposed:
            return

        items = self._get_items()

        if not isinstance(items, list):
            msg = f"each must return list, got {type(items).__name__}"
            raise TypeError(msg)

        runtime = self._runtime_ref() if self._runtime_ref else None
        render_lock = getattr(runtime, "render_lock", None) if runtime else None

        if render_lock:
            render_lock.acquire()
        try:
            with self._lock:
                new_keys = {self.key(item): item for item in items}
                old_keys = set(self._items.keys())

                new_key_sequence = tuple(self.key(item) for item in items)
                old_key_sequence = tuple(k for k in self._items if k in new_keys)
                structure_changed = (
                    new_keys.keys() != old_keys or new_key_sequence != old_key_sequence
                )

                for key in old_keys - new_keys.keys():
                    _, container = self._items.pop(key)
                    if container in self.children:
                        self.children.remove(container)

                    if hasattr(container, "dispose"):
                        container.dispose()

                new_children: list[Element] = []
                for index, item in enumerate(items):
                    item_key = self.key(item)

                    if item_key in self._items:
                        _, container = self._items[item_key]
                    else:
                        container = self._create_item_container(item, index)
                        self._items[item_key] = (item, container)

                    new_children.append(container)

                self.children = new_children

                self.invalidate_layout()

                if self._initial_sync_done and structure_changed:
                    self._trigger_runtime_rebuild()

                self._initial_sync_done = True
        finally:
            if render_lock:
                render_lock.release()

    def dispose(self) -> None:
        with self._lock:
            self._disposed = True
            if self._effect is not None:
                self._effect.dispose()
                self._effect = None
            self._items.clear()
