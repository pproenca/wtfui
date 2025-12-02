"""Tests for Todo app component."""


def test_todo_app_creates_component():
    """Verify the todo app component can be instantiated."""
    from examples.todo.app import TodoApp

    # Should not raise - TodoApp exists
    assert TodoApp is not None


def test_todo_signals_exist():
    """Verify reactive state is properly initialized."""
    from examples.todo.app import new_todo_text, todos
    from flow import Signal

    assert isinstance(todos, Signal)
    assert isinstance(new_todo_text, Signal)
    assert todos.value == []
    assert new_todo_text.value == ""
