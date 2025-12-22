from typing import Any

from wtfui.core.context import (
    get_current_parent,
    get_current_runtime,
    reset_parent,
    set_current_parent,
)


class Element:
    __slots__ = (
        "_internal_key",
        "_token",
        "children",
        "focusable",
        "key",
        "parent",
        "props",
        "tag",
    )

    def __init__(self, **props: Any) -> None:
        self.tag = self.__class__.__name__
        self.children: list[Element] = []
        self._token = None

        self.focusable = props.pop("focusable", False)
        self.key: str | None = props.pop("key", None)

        self.props = props

        self.parent: Element | None = get_current_parent()
        if self.parent is not None:
            self.parent.children.append(self)
            self.parent.invalidate_layout()

        # Generate stable internal key
        self._internal_key = self._generate_internal_key()

    def _generate_internal_key(self) -> str:
        """Generate a stable key based on user key, parent, position, and type."""
        if self.key is not None:
            return self.key

        # Build key from parent key + position + element type
        if self.parent is not None:
            parent_key = getattr(self.parent, "_internal_key", "mock")
            position = len(self.parent.children) - 1  # Current position (just appended)
            return f"{parent_key}:{position}:{self.tag}"

        # Root element without explicit key
        return f"root:{self.tag}"

    def __enter__(self) -> Element:
        self._token = set_current_parent(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._token is not None:
            reset_parent(self._token)
            self._token = None

    def __repr__(self) -> str:
        return f"<{self.tag} children={len(self.children)} />"

    def set_style(self, **style_updates: Any) -> None:
        self.props.update(style_updates)
        self.invalidate_layout()

    def invalidate_layout(self) -> None:
        if self.parent is not None:
            self.parent.invalidate_layout()

        runtime = get_current_runtime()
        if runtime is not None and hasattr(runtime, "needs_rebuild"):
            runtime.needs_rebuild = True
            runtime.is_dirty = True

    def dispose(self) -> None:
        for child in self.children:
            if hasattr(child, "dispose"):
                child.dispose()
