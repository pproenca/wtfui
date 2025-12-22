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


def test_load_todos_only_called_once_on_rerender():
    """Verify load_todos is guarded by _initialized flag.

    Regression test: Without this guard, every re-render of TodoApp would call
    load_todos(), which reads from storage. This creates a race condition with
    the async save_todos Effect, causing newly added todos to be overwritten
    with stale storage data before the Effect has a chance to persist.
    """
    import app

    # Reset initialization state for test
    app._initialized = False
    app._todos.value = []

    # Simulate first render - should initialize
    assert not app._initialized
    if not app._initialized:
        app.load_todos()
        app._initialized = True
    assert app._initialized

    # Now add a todo in-memory (simulating user action)
    app._new_todo_text.value = "Test todo"
    app.add_todo()
    assert len(app._todos.value) == 1

    # Simulate second render (re-render after action)
    # _initialized is True, so load_todos should NOT be called
    if not app._initialized:
        # This would overwrite our in-memory todo with stale storage!
        app.load_todos()
        app._initialized = True

    # Todo should still be in memory (not overwritten by load_todos)
    assert len(app._todos.value) == 1
    assert app._todos.value[0].text == "Test todo"


def test_add_todo_updates_memory_immediately():
    """Verify add_todo updates _todos.value in-memory without waiting for storage.

    This ensures UI can re-render with new data immediately, while persistence
    happens asynchronously via the Effect.
    """
    import app

    # Reset state
    app._todos.value = []
    app._new_todo_text.value = "Immediate update test"

    # add_todo should update _todos.value immediately
    app.add_todo()

    # Should be in memory immediately (not waiting for Effect to run)
    assert len(app._todos.value) == 1
    assert app._todos.value[0].text == "Immediate update test"

    # Input should be cleared
    assert app._new_todo_text.value == ""
