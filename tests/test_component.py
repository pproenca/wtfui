# tests/test_component.py
"""Tests for @component decorator."""

import asyncio

from wtfui.core.component import component
from wtfui.ui import Div, Text


def test_component_decorator_marks_function():
    """@component decorator marks function as a component."""

    @component
    async def MyComponent():
        Div()

    assert hasattr(MyComponent, "_is_wtfui_component")
    assert MyComponent._is_wtfui_component is True


def test_component_can_be_called():
    """Component can be called and returns element tree."""

    @component
    async def SimpleComponent():
        with Div(cls="simple") as root:
            Text("Hello")
        return root

    result = asyncio.run(SimpleComponent())
    assert result is not None
    assert result.tag == "Div"


def test_component_with_props():
    """Component can receive props."""

    @component
    async def Greeting(name: str):
        el = Text(f"Hello, {name}!")
        return el

    result = asyncio.run(Greeting(name="World"))
    assert result.content == "Hello, World!"


def test_component_nesting():
    """Components can nest other components."""

    @component
    async def Inner():
        el = Text("Inner")
        return el

    @component
    async def Outer():
        with Div() as root:
            await Inner()
            # In real usage, inner would be composed
        return root

    result = asyncio.run(Outer())
    assert result.tag == "Div"
