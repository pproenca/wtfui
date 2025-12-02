# src/flow/signal.py
"""Signal - A thread-safe reactive value for Python 3.14+ No-GIL builds."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class Signal(Generic[T]):
    """
    A thread-safe value that notifies subscribers when it changes.

    Uses threading.Lock for No-GIL safety in Python 3.14+.
    The lock is cheap in free-threaded builds.
    """

    def __init__(self, value: T) -> None:
        self._value: T = value
        self._subscribers: set[Callable[[], None]] = set()
        self._effects: set[Any] = set()  # Will be set[Effect] after Task 1.5
        self._lock = threading.Lock()  # No-GIL safe

    @property
    def value(self) -> T:
        """Get the current value (thread-safe read)."""
        with self._lock:
            return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the value and notify subscribers if changed (thread-safe write)."""
        with self._lock:
            if self._value != new_value:
                self._value = new_value
                self._notify_locked()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns unsubscribe function."""
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        """Remove a subscriber (thread-safe)."""
        with self._lock:
            self._subscribers.discard(callback)

    def _notify_locked(self) -> None:
        """Notify all subscribers. Must be called with lock held."""
        # Copy to allow subscribers to modify during iteration
        subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber()

    def __repr__(self) -> str:
        with self._lock:
            return f"Signal({self._value!r})"
