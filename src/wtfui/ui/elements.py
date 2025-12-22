import weakref
from typing import TYPE_CHECKING, Any

from wtfui.core.context import get_current_runtime
from wtfui.core.element import Element

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.computed import Computed
    from wtfui.core.signal import Signal


class Div(Element):
    __slots__ = ()


class VStack(Element):
    __slots__ = ()

    def __init__(self, **props: Any) -> None:
        props.setdefault("flex_direction", "column")
        super().__init__(**props)


class HStack(Element):
    __slots__ = ()

    def __init__(self, **props: Any) -> None:
        props.setdefault("flex_direction", "row")
        super().__init__(**props)


class Card(Element):
    __slots__ = ("title",)

    def __init__(self, title: str | None = None, **props: Any) -> None:
        super().__init__(**props)
        self.title = title


class Text(Element):
    __slots__ = ("_content_source", "_effect", "_runtime_ref")

    def __init__(self, content: str | Signal[Any] | Computed[Any] = "", **props: Any) -> None:
        super().__init__(**props)
        self._content_source = content
        self._effect = None

        runtime = get_current_runtime()
        self._runtime_ref = weakref.ref(runtime) if runtime is not None else None

        if hasattr(content, "value") or callable(content):
            from wtfui.core.effect import Effect

            self._effect = Effect(self._on_content_change)

    @property
    def content(self) -> str:
        source = self._content_source
        if hasattr(source, "value"):
            return str(source.value)
        if callable(source):
            return str(source())
        return str(source)

    def _on_content_change(self) -> None:
        _ = self.content
        self.invalidate_layout()

        if self._runtime_ref is not None:
            runtime = self._runtime_ref()
            if runtime is not None:
                runtime.is_dirty = True
                runtime.needs_rebuild = True

    def dispose(self) -> None:
        if self._effect:
            self._effect.dispose()
            self._effect = None
        super().dispose()

    def __enter__(self) -> Text:
        return super().__enter__()


class Button(Element):
    __slots__ = ("label",)

    def __init__(
        self,
        label: str = "",
        on_click: Callable[[], Any] | None = None,
        disabled: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(on_click=on_click, disabled=disabled, **props)
        self.label = label


class Input(Element):
    __slots__ = ("_text_value", "bind", "cursor_pos")

    def __init__(
        self,
        bind: Signal[str] | None = None,
        placeholder: str = "",
        on_change: Callable[[str], Any] | None = None,
        **props: Any,
    ) -> None:
        props.setdefault("focusable", True)

        props["on_keydown"] = self.handle_keydown
        super().__init__(placeholder=placeholder, on_change=on_change, **props)
        self.bind = bind

        self._text_value = bind.value if bind is not None else ""
        self.cursor_pos = len(self._text_value)

    @property
    def text_value(self) -> str:
        if self.bind is not None:
            return self.bind.value
        return self._text_value

    @text_value.setter
    def text_value(self, value: str) -> None:
        if self.bind is not None:
            self.bind.value = value
        else:
            self._text_value = value

        on_change = self.props.get("on_change")
        if on_change is not None:
            on_change(value)

    def handle_keydown(self, key: str) -> None:
        if key == "backspace":
            if self.cursor_pos > 0:
                text = self.text_value
                self.text_value = text[: self.cursor_pos - 1] + text[self.cursor_pos :]
                self.cursor_pos -= 1
        elif key == "left":
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
        elif key == "right":
            if self.cursor_pos < len(self.text_value):
                self.cursor_pos += 1
        elif len(key) == 1 and key.isprintable():
            text = self.text_value
            self.text_value = text[: self.cursor_pos] + key + text[self.cursor_pos :]
            self.cursor_pos += 1


class Window(Element):
    __slots__ = ()

    def __init__(
        self,
        title: str = "WtfUI App",
        theme: str = "light",
        **props: Any,
    ) -> None:
        super().__init__(title=title, theme=theme, **props)
