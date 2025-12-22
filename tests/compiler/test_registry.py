"""Tests for component registry."""

import ast

from wtfui.web.compiler.registry import ComponentRegistry


def test_register_component_function() -> None:
    """Registry tracks @component decorated functions."""
    source = """
from wtfui import component

@component
async def MyCard():
    with Div():
        Text("Hello")
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    assert "MyCard" in registry
    assert registry.get("MyCard") is not None


def test_registry_returns_function_body() -> None:
    """Registry provides access to component AST body."""
    source = """
@component
async def Counter():
    count = Signal(0)
    Text(f"Count: {count.value}")
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    body = registry.get_body("Counter")
    assert body is not None
    assert len(body) == 2  # Signal assignment + Text call


def test_registry_ignores_non_component_functions() -> None:
    """Registry skips functions without @component decorator."""
    source = """
def helper():
    return 42

@component
async def App():
    Text("hi")
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    assert "helper" not in registry
    assert "App" in registry


def test_registry_rejects_component_with_positional_args() -> None:
    """Registry rejects components with positional parameters."""
    source = """
@component
async def Card(title):
    with Div():
        Text(title)
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    # Component with parameters should be rejected
    assert "Card" not in registry


def test_registry_rejects_component_with_keyword_args() -> None:
    """Registry rejects components with keyword-only parameters."""
    source = """
@component
async def Dialog(*, open=False):
    with Div():
        Text("Content")
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    # Component with keyword-only parameters should be rejected
    assert "Dialog" not in registry


def test_registry_rejects_component_with_varargs() -> None:
    """Registry rejects components with *args or **kwargs."""
    source = """
@component
async def Container(*children):
    with Div():
        pass
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    # Component with *args should be rejected
    assert "Container" not in registry


def test_registry_accepts_component_without_args() -> None:
    """Registry accepts components with no parameters."""
    source = """
@component
async def SimpleCard():
    with Div():
        Text("Hello")
"""
    tree = ast.parse(source)
    registry = ComponentRegistry()
    registry.scan(tree)

    # Component without parameters should be accepted
    assert "SimpleCard" in registry
