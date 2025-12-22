# tests/test_context.py
"""Tests for context stack - parent tracking during rendering."""

from wtfui.core.context import get_current_parent, reset_parent, set_current_parent


def test_context_stack_initially_none():
    """The parent context starts as None."""
    assert get_current_parent() is None


def test_context_stack_set_and_get():
    """Setting a parent makes it retrievable."""
    parent = object()
    token = set_current_parent(parent)
    try:
        assert get_current_parent() is parent
    finally:
        reset_parent(token)


def test_context_stack_nesting():
    """Context can be nested and restored."""
    parent1 = object()
    parent2 = object()

    token1 = set_current_parent(parent1)
    try:
        assert get_current_parent() is parent1
        token2 = set_current_parent(parent2)
        try:
            assert get_current_parent() is parent2
        finally:
            reset_parent(token2)
        assert get_current_parent() is parent1
    finally:
        reset_parent(token1)
