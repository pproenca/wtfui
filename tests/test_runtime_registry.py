"""Tests for element registry and event routing."""

from wtfui.core.registry import ElementRegistry
from wtfui.ui import Button, Div


def test_registry_stores_elements_by_id():
    """Registry stores elements indexed by their ID."""
    registry = ElementRegistry()

    btn = Button("Click me")
    registry.register(btn)

    retrieved = registry.get(id(btn))
    assert retrieved is btn


def test_registry_finds_handler():
    """Registry can find event handlers for elements."""
    registry = ElementRegistry()

    handler_called = []
    btn = Button("Test", on_click=lambda: handler_called.append(True))
    registry.register(btn)

    handler = registry.get_handler(id(btn), "click")
    assert handler is not None

    handler()
    assert handler_called == [True]


def test_registry_returns_none_for_missing():
    """Registry returns None for unregistered elements."""
    registry = ElementRegistry()

    assert registry.get(999999) is None
    assert registry.get_handler(999999, "click") is None


def test_registry_clears_on_rerender():
    """Registry can be cleared for fresh renders."""
    registry = ElementRegistry()

    btn = Button("Test")
    registry.register(btn)
    assert registry.get(id(btn)) is not None

    registry.clear()
    assert registry.get(id(btn)) is None


def test_registry_builds_from_tree():
    """Registry can register all elements from a tree."""
    registry = ElementRegistry()

    with Div() as root:
        btn1 = Button("One", on_click=lambda: None)
        btn2 = Button("Two", on_click=lambda: None)

    registry.register_tree(root)

    assert registry.get(id(root)) is root
    assert registry.get(id(btn1)) is btn1
    assert registry.get(id(btn2)) is btn2
