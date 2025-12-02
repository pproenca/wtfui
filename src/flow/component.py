# src/flow/component.py
"""Component decorator for Flow UI components (PEP 649 lazy injection)."""

from __future__ import annotations

import inspect
import sys
from functools import wraps
from typing import Any, get_type_hints

from flow.injection import get_provider


def _get_lazy_annotations(fn: Any) -> dict[str, Any]:
    """
    Get type annotations with deferred evaluation (PEP 649 compatible).

    In Python 3.14+, uses annotationlib for lazy evaluation.
    Falls back to get_type_hints with error handling for older versions.
    """
    # Python 3.14+: Use annotationlib for deferred evaluation
    if sys.version_info >= (3, 14):
        try:
            import annotationlib

            # Get annotations in VALUE format (fully resolved)
            return annotationlib.get_annotations(
                fn,
                format=annotationlib.Format.VALUE,
                eval_str=True,
            )
        except Exception:  # noqa: S110 - Fallback is intentional
            pass  # Fall through to get_type_hints fallback

    # Python 3.12-3.13: Use get_type_hints with delayed evaluation
    try:
        # Get the function's global namespace for forward ref resolution
        globalns = getattr(fn, "__globals__", {})
        return get_type_hints(fn, globalns=globalns, include_extras=True)
    except Exception:
        # If all else fails, return raw annotations
        return getattr(fn, "__annotations__", {})


def component(fn: Any) -> Any:
    """
    Decorator that marks an async function as a Flow component.

    Components are async functions that build UI using context managers.
    They can receive props as parameters and use dependency injection.

    Uses PEP 649 deferred annotation evaluation to support:
    - Forward references
    - Circular dependencies (enterprise patterns)
    - Late binding of types
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # LAZY: Get type hints only when component is actually called
        # This enables circular dependencies and forward references
        hints = _get_lazy_annotations(fn)

        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())

        # Build the full kwargs with injected dependencies
        final_kwargs = dict(kwargs)

        # Count positional args already provided
        provided_positional = len(args)

        for i, param_name in enumerate(params):
            # Skip if already provided as positional arg
            if i < provided_positional:
                continue

            # Skip if already provided as keyword arg
            if param_name in final_kwargs:
                continue

            # Try to inject based on type hint
            if param_name in hints:
                hint_type = hints[param_name]
                provider = get_provider(hint_type)
                if provider is not None:
                    final_kwargs[param_name] = provider

        return await fn(*args, **final_kwargs)

    # Mark as a component for introspection
    wrapper._is_flow_component = True  # type: ignore[attr-defined]
    wrapper._original_fn = fn  # type: ignore[attr-defined]

    return wrapper
