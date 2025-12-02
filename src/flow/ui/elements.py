# src/flow/ui/elements.py
"""UI Elements - The building blocks of Flow interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flow.element import Element

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.signal import Signal


class Div(Element):
    """A generic container element."""


class VStack(Element):
    """A vertical stack layout container."""


class HStack(Element):
    """A horizontal stack layout container."""


class Card(Element):
    """A card container with optional title."""

    def __init__(self, title: str | None = None, **props: Any) -> None:
        super().__init__(**props)
        self.title = title


class Text(Element):
    """A text content element."""

    def __init__(self, content: str = "", **props: Any) -> None:
        super().__init__(**props)
        self.content = content

    def __enter__(self) -> Text:
        # Text elements typically don't have children, but support it for consistency
        return super().__enter__()  # type: ignore[return-value]


class Button(Element):
    """A clickable button element."""

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
    """A text input element with optional Signal binding."""

    def __init__(
        self,
        bind: Signal[str] | None = None,
        placeholder: str = "",
        on_change: Callable[[str], Any] | None = None,
        **props: Any,
    ) -> None:
        super().__init__(placeholder=placeholder, on_change=on_change, **props)
        self.bind = bind


class Window(Element):
    """A top-level window container."""

    def __init__(
        self,
        title: str = "Flow App",
        theme: str = "light",
        **props: Any,
    ) -> None:
        super().__init__(title=title, theme=theme, **props)
