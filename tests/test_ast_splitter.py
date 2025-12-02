# tests/test_ast_splitter.py
"""Tests for AST Splitter - Zero-Build Developer Experience."""

from flow.dev.splitter import split_server_client

MIXED_SOURCE = """
from flow import component
from flow.rpc import rpc
from flow.ui import Div, Text, Button

@rpc
async def fetch_data(user_id: int) -> dict:
    # This runs on SERVER
    return {"id": user_id, "name": "Alice"}

@component
async def UserCard(user_id: int):
    with Div(cls="card"):
        with Text(f"User {user_id}"):
            pass
        with Button(on_click=lambda: fetch_data(user_id)):
            pass
"""


def test_split_identifies_server_code():
    """Splitter extracts @rpc decorated functions."""
    server_code, _client_code = split_server_client(MIXED_SOURCE)

    assert "fetch_data" in server_code
    assert "@rpc" in server_code
    assert "user_id" in server_code  # Function parameter preserved


def test_split_identifies_client_code():
    """Splitter extracts @component decorated functions."""
    _server_code, client_code = split_server_client(MIXED_SOURCE)

    assert "UserCard" in client_code
    assert "@component" in client_code


def test_split_preserves_imports():
    """Both server and client code get necessary imports."""
    server_code, client_code = split_server_client(MIXED_SOURCE)

    # Server needs rpc import
    assert "from flow.rpc import rpc" in server_code

    # Client needs component and UI imports
    assert "from flow import component" in client_code
    assert "from flow.ui import" in client_code


def test_split_returns_empty_for_pure_server():
    """Pure server code returns empty client."""
    pure_server = """
from flow.rpc import rpc

@rpc
async def server_only():
    return 42
"""
    server_code, client_code = split_server_client(pure_server)

    assert "server_only" in server_code
    assert "server_only" not in client_code or client_code.strip() == ""


def test_split_returns_empty_for_pure_client():
    """Pure client code returns empty server."""
    pure_client = """
from flow import component
from flow.ui import Div

@component
async def ClientOnly():
    with Div():
        pass
"""
    server_code, client_code = split_server_client(pure_client)

    assert "ClientOnly" in client_code
    assert "ClientOnly" not in server_code or server_code.strip() == ""
