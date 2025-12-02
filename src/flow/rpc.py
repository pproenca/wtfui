# src/flow/rpc.py
"""RPC - Remote Procedure Call system for server/client communication."""

from __future__ import annotations

import sys
from functools import wraps
from typing import Any, ClassVar

# Detect environment
IS_SERVER = not (sys.platform == "emscripten" or sys.platform == "wasi")


class RpcRegistry:
    """Registry for server-side RPC function implementations."""

    routes: ClassVar[dict[str, Any]] = {}

    @classmethod
    def clear(cls) -> None:
        """Clear all registered routes."""
        cls.routes = {}

    @classmethod
    def get(cls, name: str) -> Any | None:
        """Get a registered function by name."""
        return cls.routes.get(name)


def rpc(func: Any) -> Any:
    """
    Decorator that registers a function as an RPC endpoint.

    On the server: Registers the function and keeps it callable.
    On the client (Wasm): Would replace with a fetch() proxy.
    """
    if IS_SERVER:
        # Server mode: Register and return the original function
        RpcRegistry.routes[func.__name__] = func

        @wraps(func)
        async def server_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return server_wrapper
    else:
        # Client mode (Wasm): Would be replaced with fetch proxy
        # For now, just return the function for testing
        return func
