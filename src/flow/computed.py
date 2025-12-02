# src/flow/computed.py
"""Computed - Memoized values that auto-update on signal changes."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

# Track which Computed is currently being evaluated (for signal tracking)
_evaluating_computed: ContextVar[Computed[Any] | None] = ContextVar(
    "evaluating_computed", default=None
)


def get_evaluating_computed() -> Computed[Any] | None:
    """Get the Computed currently being evaluated."""
    return _evaluating_computed.get()


class Computed(Generic[T]):
    """
    A memoized computed value that tracks Signal dependencies.

    Automatically re-computes when any accessed Signal changes.
    """

    def __init__(self, fn: Callable[[], T]) -> None:
        self.fn = fn
        self._value: T | None = None
        self._is_dirty: bool = True

    def __call__(self) -> T:
        """Get the computed value, recomputing if necessary."""
        if self._is_dirty:
            self._recompute()
        return self._value  # type: ignore[return-value]

    def _recompute(self) -> None:
        """Recompute the value while tracking dependencies."""
        # Set self as the currently evaluating computed
        token = _evaluating_computed.set(self)
        try:
            self._value = self.fn()
            self._is_dirty = False
        finally:
            _evaluating_computed.reset(token)

    def invalidate(self) -> None:
        """Mark this computed as needing recalculation."""
        self._is_dirty = True

    def __repr__(self) -> str:
        return f"Computed({self.fn.__name__}, dirty={self._is_dirty})"
