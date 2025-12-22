"""Tests for Todo app component."""


def test_todo_app_creates_component():
    """Verify the todo app component can be instantiated."""
    from app import TodoApp

    # Should not raise - TodoApp exists
    assert TodoApp is not None


def test_todo_signals_exist():
    """Verify reactive state is properly initialized."""
    from app import _new_todo_text, _todos

    from wtfui import Signal

    assert isinstance(_todos, Signal)
    assert isinstance(_new_todo_text, Signal)
    assert _todos.value == []
    assert _new_todo_text.value == ""


def test_add_todo_rejects_empty_text():
    """Verify add_todo does not create todos with empty/whitespace text."""
    from app import _new_todo_text, _todos, add_todo

    # Reset state
    _todos.value = []

    # Try to add empty todo
    _new_todo_text.value = "   "  # whitespace only
    add_todo()

    assert len(_todos.value) == 0, "Empty text should not create a todo"


def test_add_todo_rejects_too_long_text():
    """Verify add_todo rejects text over 500 characters."""
    from app import _new_todo_text, _todos, add_todo

    # Reset state
    _todos.value = []

    # Try to add overly long todo
    _new_todo_text.value = "x" * 501
    add_todo()

    assert len(_todos.value) == 0, "Text over 500 chars should not create a todo"
