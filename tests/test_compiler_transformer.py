"""Tests for client-safe AST transformation."""

import pytest

from flow.compiler.transformer import transform_for_client


def test_transformer_keeps_component():
    """Client bundle keeps @component decorated functions."""
    source = """
from flow import component
from flow.ui import Div

@component
async def MyApp():
    with Div():
        pass
"""
    result = transform_for_client(source)

    assert "@component" in result
    assert "async def MyApp" in result


def test_transformer_stubs_rpc_body():
    """@rpc function bodies are replaced with fetch stub."""
    source = """
from flow import rpc
import sqlalchemy

@rpc
async def save_to_db(data: str):
    db = sqlalchemy.connect()
    db.save(data)
    return "saved"
"""
    # Expect warning about removed server import
    with pytest.warns(UserWarning, match="Removed server-only import"):
        result = transform_for_client(source)

    assert "@rpc" in result
    assert "async def save_to_db" in result
    # Body should be stubbed - no server code
    assert "sqlalchemy.connect" not in result
    # Should have fetch stub
    assert "fetch" in result.lower() or "pass" in result


def test_transformer_removes_server_imports():
    """Server-only imports are removed from client bundle."""
    source = """
import sqlalchemy
import pandas as pd
import boto3
from flow import component

@component
async def App():
    pass
"""
    # Expect warnings about removed server imports
    with pytest.warns(UserWarning, match="Removed server-only import"):
        result = transform_for_client(source)

    assert "import sqlalchemy" not in result
    assert "import pandas" not in result
    assert "import boto3" not in result
    assert "from flow import component" in result


def test_transformer_preserves_ui_code():
    """UI code and state management is fully preserved."""
    source = """
from flow import Signal, component
from flow.ui import Text

class AppState:
    count = Signal(0)

@component
async def Counter(state: AppState):
    state.count.value += 1
"""
    result = transform_for_client(source)

    assert "class AppState" in result
    assert "count = Signal(0)" in result
    assert "state.count.value += 1" in result


def test_transformer_detects_dangerous_imports():
    """Transformer raises warning for dangerous server imports in client context."""
    source = """
import os
from flow import component

@component
async def App():
    # This would leak env vars to client!
    api_key = os.environ["SECRET_KEY"]
"""
    # Should not crash but should remove os import and warn
    with pytest.warns(UserWarning, match="Removed server-only import"):
        result = transform_for_client(source)

    assert "import os" not in result


def test_transformer_handles_nested_decorators():
    """Handles functions with multiple decorators."""
    source = """
from flow import rpc
from functools import cache

@cache
@rpc
async def expensive_query(x: int):
    return x * 2
"""
    result = transform_for_client(source)

    # @rpc should be preserved, body stubbed
    assert "@rpc" in result
    assert "x * 2" not in result  # Body stubbed
