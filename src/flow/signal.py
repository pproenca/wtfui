# src/flow/signal.py
"""Signal - A thread-safe reactive value for Python 3.14+ No-GIL builds."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.computed import Computed
    from flow.effect import Effect

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
        self._effects: set[Effect] = set()
        self._computeds: set[Computed[Any]] = set()
        self._lock = threading.Lock()  # No-GIL safe

    @property
    def value(self) -> T:
        """Get the current value and track effect/computed dependency (thread-safe)."""
        from flow.computed import get_evaluating_computed
        from flow.effect import get_running_effect

        with self._lock:
            # Track effect dependency if one is currently running
            effect = get_running_effect()
            if effect is not None:
                self._effects.add(effect)

            # Track computed dependency if one is currently evaluating
            computed = get_evaluating_computed()
            if computed is not None:
                self._computeds.add(computed)

            return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the value and notify subscribers if changed (thread-safe write)."""
        subscribers_to_notify: list[Callable[[], None]] = []
        effects_to_schedule: list[Effect] = []
        computeds_to_invalidate: list[Computed[Any]] = []

        with self._lock:
            if self._value != new_value:
                self._value = new_value
                # Copy while holding lock, notify AFTER releasing
                subscribers_to_notify = list(self._subscribers)
                effects_to_schedule = list(self._effects)
                computeds_to_invalidate = list(self._computeds)

        # Notify OUTSIDE the lock to prevent deadlock
        for subscriber in subscribers_to_notify:
            subscriber()

        for effect in effects_to_schedule:
            effect.schedule()

        for computed in computeds_to_invalidate:
            computed.invalidate()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns unsubscribe function."""
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        """Remove a subscriber (thread-safe)."""
        with self._lock:
            self._subscribers.discard(callback)

    def __repr__(self) -> str:
        with self._lock:
            return f"Signal({self._value!r})"
