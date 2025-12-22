import inspect
from functools import wraps
from typing import Any, get_type_hints

from wtfui.core.injection import get_provider


def _get_lazy_annotations(fn: Any) -> dict[str, Any]:
    """Get type annotations using cascading fallback methods."""
    # Method 1: Python 3.14+ annotationlib (preferred)
    try:
        import annotationlib

        return annotationlib.get_annotations(
            fn,
            format=annotationlib.Format.VALUE,
            eval_str=True,
        )
    except (ImportError, TypeError, NameError):
        pass  # annotationlib not available or evaluation failed

    # Method 2: typing.get_type_hints (standard library)
    try:
        globalns = getattr(fn, "__globals__", {})
        return get_type_hints(fn, globalns=globalns, include_extras=True)
    except Exception:
        # Method 3: Raw __annotations__ (last resort)
        return getattr(fn, "__annotations__", {})


def component(fn: Any) -> Any:
    def _inject_dependencies(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        hints = _get_lazy_annotations(fn)
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())

        final_kwargs = dict(kwargs)
        provided_positional = len(args)

        for i, param_name in enumerate(params):
            if i < provided_positional:
                continue
            if param_name in final_kwargs:
                continue
            if param_name in hints:
                hint_type = hints[param_name]
                provider = get_provider(hint_type)
                if provider is not None:
                    final_kwargs[param_name] = provider

        return final_kwargs

    if inspect.iscoroutinefunction(fn):

        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            final_kwargs = _inject_dependencies(args, kwargs)
            return await fn(*args, **final_kwargs)

        async_wrapper._is_wtfui_component = True
        async_wrapper._original_fn = fn
        return async_wrapper
    else:

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            final_kwargs = _inject_dependencies(args, kwargs)
            return fn(*args, **final_kwargs)

        sync_wrapper._is_wtfui_component = True
        sync_wrapper._original_fn = fn
        return sync_wrapper
