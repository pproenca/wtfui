# tests/test_component.py
"""Tests for @component decorator."""

import asyncio

from flow.component import component
from flow.ui import Div, Text


def test_component_decorator_marks_function():
    """@component decorator marks function as a component."""

    @component
    async def MyComponent():
        with Div():
            pass

    assert hasattr(MyComponent, "_is_flow_component")
    assert MyComponent._is_flow_component is True


def test_component_can_be_called():
    """Component can be called and returns element tree."""

    @component
    async def SimpleComponent():
        with Div(cls="simple") as root, Text("Hello"):
            pass
        return root

    result = asyncio.run(SimpleComponent())
    assert result is not None
    assert result.tag == "Div"


def test_component_with_props():
    """Component can receive props."""

    @component
    async def Greeting(name: str):
        with Text(f"Hello, {name}!") as el:
            pass
        return el

    result = asyncio.run(Greeting(name="World"))
    assert result.content == "Hello, World!"


def test_component_nesting():
    """Components can nest other components."""

    @component
    async def Inner():
        with Text("Inner") as el:
            pass
        return el

    @component
    async def Outer():
        with Div() as root:
            await Inner()
            # In real usage, inner would be composed
        return root

    result = asyncio.run(Outer())
    assert result.tag == "Div"
