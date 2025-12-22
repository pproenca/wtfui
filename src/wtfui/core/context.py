from contextvars import ContextVar, Token
from typing import Any

_current_parent: ContextVar[Any | None] = ContextVar("fuse_parent", default=None)


def get_current_parent() -> Any | None:
    return _current_parent.get()


def set_current_parent(parent: Any) -> Token[Any | None]:
    return _current_parent.set(parent)


def reset_parent(token: Token[Any | None]) -> None:
    _current_parent.reset(token)


_current_runtime: ContextVar[Any] = ContextVar("current_runtime", default=None)


def get_current_runtime() -> Any:
    return _current_runtime.get()


def set_current_runtime(runtime: Any) -> Token[Any]:
    return _current_runtime.set(runtime)


def reset_runtime(token: Token[Any]) -> None:
    _current_runtime.reset(token)
