# tests/test_rpc.py
"""Tests for @rpc decorator and RpcRegistry."""

import asyncio

from flow.rpc import RpcRegistry, rpc


def test_rpc_registers_function():
    """@rpc decorator registers function in registry."""
    RpcRegistry.clear()

    @rpc
    async def my_server_function(x: int) -> int:
        return x * 2

    assert "my_server_function" in RpcRegistry.routes


def test_rpc_function_still_callable():
    """Decorated function can still be called directly."""
    RpcRegistry.clear()

    @rpc
    async def add(a: int, b: int) -> int:
        return a + b

    result = asyncio.run(add(2, 3))
    assert result == 5


def test_rpc_stores_function_reference():
    """Registry stores the actual function."""
    RpcRegistry.clear()

    @rpc
    async def compute():
        return 42

    stored_fn = RpcRegistry.routes["compute"]
    result = asyncio.run(stored_fn())
    assert result == 42


def test_rpc_multiple_functions():
    """Multiple functions can be registered."""
    RpcRegistry.clear()

    @rpc
    async def func_a():
        pass

    @rpc
    async def func_b():
        pass

    assert len(RpcRegistry.routes) == 2
    assert "func_a" in RpcRegistry.routes
    assert "func_b" in RpcRegistry.routes
