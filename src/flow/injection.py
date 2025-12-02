# src/flow/injection.py
"""Dependency injection for Flow components (Thread-Safe, PEP 649 ready)."""

from __future__ import annotations

import threading
from contextvars import ContextVar
from typing import Any, TypeVar

T = TypeVar("T")

# Thread-safe global registry for provided dependencies
_providers: ContextVar[dict[type[Any], Any] | None] = ContextVar("providers", default=None)
_providers_lock = threading.Lock()


def provide(type_: type[T], instance: T) -> None:
    """Register an instance as the provider for a type (thread-safe)."""
    with _providers_lock:
        providers = _providers.get() or {}
        new_providers = {**providers, type_: instance}
        _providers.set(new_providers)


def get_provider(type_: type[T]) -> T | None:
    """Get the registered provider for a type (thread-safe)."""
    with _providers_lock:
        providers = _providers.get() or {}
        return providers.get(type_)


def clear_providers() -> None:
    """Clear all registered providers (thread-safe)."""
    with _providers_lock:
        _providers.set(None)
