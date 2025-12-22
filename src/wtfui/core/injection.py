import threading
from contextvars import ContextVar
from typing import Any

_providers: ContextVar[dict[type[Any], Any] | None] = ContextVar("providers", default=None)
_providers_lock = threading.Lock()


def provide[T](type_: type[T], instance: T) -> None:
    with _providers_lock:
        providers = _providers.get() or {}
        new_providers = {**providers, type_: instance}
        _providers.set(new_providers)


def get_provider[T](type_: type[T]) -> T | None:
    with _providers_lock:
        providers = _providers.get() or {}
        return providers.get(type_)


def clear_providers() -> None:
    with _providers_lock:
        _providers.set(None)
