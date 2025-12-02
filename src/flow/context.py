# src/flow/context.py
"""Context stack for tracking the current parent element during rendering."""

from contextvars import ContextVar, Token
from typing import Any

# Tracks the current 'parent' element being rendered
_current_parent: ContextVar[Any | None] = ContextVar("flow_parent", default=None)


def get_current_parent() -> Any | None:
    """Get the current parent element from the context stack."""
    return _current_parent.get()


def set_current_parent(parent: Any) -> Token[Any | None]:
    """Push a new parent onto the context stack. Returns a token for reset."""
    return _current_parent.set(parent)


def reset_parent(token: Token[Any | None]) -> None:
    """Pop the parent from the context stack using the token."""
    _current_parent.reset(token)
