# src/flow/component.py
"""Component decorator for Flow UI components."""

from __future__ import annotations

from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def component(
    fn: Any,  # Callable[P, Coroutine[Any, Any, R]]
) -> Any:  # Callable[P, Coroutine[Any, Any, R]]
    """
    Decorator that marks an async function as a Flow component.

    Components are async functions that build UI using context managers.
    They can receive props as parameters and optionally use dependency injection.
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # In a full implementation, this would:
        # 1. Look up dependencies from type hints
        # 2. Inject them into the call
        # 3. Track the component in the render tree
        return await fn(*args, **kwargs)

    # Mark as a component for introspection
    wrapper._is_flow_component = True  # type: ignore[attr-defined]
    wrapper._original_fn = fn  # type: ignore[attr-defined]

    return wrapper
