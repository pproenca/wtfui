# src/flow/effect.py
"""Effect - Thread-safe dependency tracking for Python 3.14+ No-GIL builds."""

from __future__ import annotations

import threading
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# ContextVar is per-thread in No-GIL builds, providing natural isolation
_running_effect: ContextVar[Effect | None] = ContextVar("running_effect", default=None)


def get_running_effect() -> Effect | None:
    """Get the currently executing effect (thread-local via ContextVar)."""
    return _running_effect.get()


class Effect:
    """
    Wraps a function to track Signal usage and re-run on changes.

    Thread-safe for Python 3.14+ No-GIL builds.
    """

    def __init__(self, fn: Callable[[], None]) -> None:
        self.fn = fn
        self._lock = threading.Lock()
        self._scheduled = False
        self.run()

    def schedule(self) -> None:
        """Schedule this effect for re-execution (thread-safe, deduped)."""
        with self._lock:
            if self._scheduled:
                return
            self._scheduled = True

        # In a full implementation, this would go to an event loop
        # For now, execute synchronously
        self.run()

    def run(self) -> None:
        """Execute the function while tracking as the active effect."""
        with self._lock:
            self._scheduled = False

        token = _running_effect.set(self)
        try:
            self.fn()
        finally:
            _running_effect.reset(token)

    def __repr__(self) -> str:
        return f"Effect({self.fn.__name__})"
