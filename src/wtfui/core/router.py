import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class HistoryState:
    __slots__ = ("_cursor", "_lock", "_stack", "_subscribers")

    def __init__(self, initial_path: str = "/") -> None:
        self._stack = [initial_path]
        self._cursor = 0
        self._subscribers = []
        self._lock = threading.RLock()

    @property
    def stack(self) -> list[str]:
        with self._lock:
            return list(self._stack)

    @property
    def cursor(self) -> int:
        with self._lock:
            return self._cursor

    @property
    def current_path(self) -> str:
        with self._lock:
            return self._stack[self._cursor]

    def push(self, path: str) -> None:
        with self._lock:
            self._stack = self._stack[: self._cursor + 1]
            self._stack.append(path)
            self._cursor = len(self._stack) - 1
            self._notify(path)

    def back(self) -> None:
        with self._lock:
            if self._cursor > 0:
                self._cursor -= 1
                self._notify(self._stack[self._cursor])

    def forward(self) -> None:
        with self._lock:
            if self._cursor < len(self._stack) - 1:
                self._cursor += 1
                self._notify(self._stack[self._cursor])

    def subscribe(self, callback: Callable[[str], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self, path: str) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(path)


@dataclass(frozen=True)
class Route:
    path: str
    component: Callable[..., Any]

    def match(self, path: str) -> dict[str, str] | None:
        pattern = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", self.path)
        pattern = f"^{pattern}$"

        match = re.match(pattern, path)
        if match:
            return match.groupdict()
        return None


@dataclass
class Router:
    routes: list[Route]
    _history: HistoryState | None = field(default=None)
    _current_path: str = field(default="/")

    def match(self, path: str) -> Callable[..., Any] | None:
        for route in self.routes:
            if route.match(path) is not None:
                return route.component
        return None

    def match_with_params(self, path: str) -> tuple[Callable[..., Any] | None, dict[str, str]]:
        for route in self.routes:
            params = route.match(path)
            if params is not None:
                return (route.component, params)
        return (None, {})

    def bind_history(self, history: HistoryState) -> None:
        self._history = history
        self._current_path = history.current_path

        def on_change(path: str) -> None:
            self._current_path = path

        history.subscribe(on_change)

    def current_component(self) -> Callable[..., Any] | None:
        return self.match(self._current_path)


def handle_navigation_key(
    history: HistoryState,
    key: str,
    alt: bool = False,
    ctrl: bool = False,
) -> bool:
    if alt and key == "left":
        history.back()
        return True

    if alt and key == "right":
        history.forward()
        return True

    return False
