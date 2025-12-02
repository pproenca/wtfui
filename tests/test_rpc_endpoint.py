# tests/test_rpc_endpoint.py
"""Tests for RPC endpoint in FastAPI server."""

from fastapi.testclient import TestClient

from flow.component import component
from flow.rpc import RpcRegistry, rpc
from flow.server.app import create_app
from flow.ui import Div


@component
async def DummyApp():
    with Div() as root:
        pass
    return root


def test_rpc_endpoint_calls_function():
    """POST /api/rpc/{name} calls the registered function."""
    RpcRegistry.clear()

    @rpc
    async def multiply(a: int, b: int) -> int:
        return a * b

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post("/api/rpc/multiply", json={"a": 6, "b": 7})

    assert response.status_code == 200
    assert response.json() == 42


def test_rpc_endpoint_not_found():
    """POST to unknown function returns 404."""
    RpcRegistry.clear()

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post("/api/rpc/unknown_func", json={})

    assert response.status_code == 404


def test_rpc_endpoint_with_string_result():
    """RPC can return string results."""
    RpcRegistry.clear()

    @rpc
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    app = create_app(DummyApp)
    client = TestClient(app)

    response = client.post("/api/rpc/greet", json={"name": "World"})

    assert response.status_code == 200
    assert response.json() == "Hello, World!"
