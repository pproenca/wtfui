# examples/todo/app.py
"""Todo App - Demonstrates Signal reactivity and context manager UI.

This example showcases:
- Signal[T] for reactive state
- Effect for side effects (persistence)
- Context manager UI (with Flex():)
- Event handlers (on_click, on_change)

Run with: cd examples/todo && uv run wtfui dev --web
"""

import json
from dataclasses import dataclass, field
from uuid import uuid4

from storage import LocalStorage

from wtfui import Effect, Element, Signal, component
from wtfui.ui import Button, Flex, Input, Text
from wtfui.web.server import create_app


@dataclass
class Todo:
    """A single todo item."""

    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    completed: bool = False


# Reactive state (module-level, prefixed with underscore per naming standard)
_todos: Signal[list[Todo]] = Signal([])
_new_todo_text: Signal[str] = Signal("")

# Persistence
_storage = LocalStorage()

# Validation constants
_MAX_TODO_LENGTH = 500

# Initialization state (prevents load_todos from overwriting in-memory state on re-render)
_initialized: bool = False


def load_todos() -> None:
    """Load todos from storage."""
    data = _storage.get_item("todos")
    if data:
        items = json.loads(data)
        _todos.value = [Todo(**item) for item in items]


def save_todos() -> None:
    """Save todos to storage."""
    data = [{"id": t.id, "text": t.text, "completed": t.completed} for t in _todos.value]
    _storage.set_item("todos", json.dumps(data))


# Effect for persistence - runs on every todos change
Effect(save_todos)


def add_todo() -> None:
    """Add a new todo from input.

    Validates:
    - Text is not empty/whitespace
    - Text is not longer than _MAX_TODO_LENGTH characters
    """
    text = _new_todo_text.value.strip()
    if not text:
        return  # Reject empty text
    if len(text) > _MAX_TODO_LENGTH:
        return  # Reject overly long text
    _todos.value = [*_todos.value, Todo(text=text)]
    _new_todo_text.value = ""


def toggle_todo(todo_id: str) -> None:
    """Toggle a todo's completed status."""
    _todos.value = [
        Todo(
            id=t.id,
            text=t.text,
            completed=not t.completed if t.id == todo_id else t.completed,
        )
        for t in _todos.value
    ]


def delete_todo(todo_id: str) -> None:
    """Delete a todo by ID."""
    _todos.value = [t for t in _todos.value if t.id != todo_id]


@component
async def TodoItem(todo: Todo) -> Element:
    """A single todo item component."""
    # Capture todo.id by value using default argument to avoid closure issues
    todo_id = todo.id

    item_cls = (
        "flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
    )
    if todo.completed:
        item_cls += " opacity-60"

    check_cls = "w-8 h-8 flex items-center justify-center rounded-full border-2 transition-colors"
    if todo.completed:
        check_cls += " bg-green-500 border-green-500 text-white"
    else:
        check_cls += " border-gray-300 text-gray-400 hover:border-green-400"

    text_cls = "flex-1 line-through text-gray-400" if todo.completed else "flex-1 text-gray-700"

    with Flex(direction="row", cls=item_cls) as item:
        Button(
            label="✓" if todo.completed else "○",
            on_click=lambda tid=todo_id: toggle_todo(tid),  # type: ignore[misc]
            cls=check_cls,
        )
        Text(todo.text, cls=text_cls)
        Button(
            label="x",
            on_click=lambda tid=todo_id: delete_todo(tid),  # type: ignore[misc]
            cls="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors",
        )
    return item


@component
async def TodoApp() -> Element:
    """Main todo application component."""
    # Load persisted todos only on initial render (not re-renders)
    # This prevents race condition with async save_todos Effect
    global _initialized
    if not _initialized:
        load_todos()
        _initialized = True

    with Flex(direction="column", cls="min-h-screen bg-gray-50 py-12 px-4") as app:
        # Centered card container
        with Flex(
            direction="column", cls="max-w-md mx-auto bg-white rounded-xl shadow-lg p-6 space-y-6"
        ):
            Text("Todo App", cls="text-2xl font-bold text-gray-800")

            # Input row
            with Flex(direction="row", cls="gap-3"):
                Input(
                    bind=_new_todo_text,
                    placeholder="What needs to be done?",
                    cls="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                )
                Button(
                    label="Add",
                    on_click=add_todo,
                    cls="px-4 py-2 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 transition-colors",
                )

            # Todo list
            with Flex(direction="column", cls="space-y-2"):
                for todo in _todos.value:
                    await TodoItem(todo)

            # Stats
            completed = len([t for t in _todos.value if t.completed])
            total = len(_todos.value)
            Text(f"{completed}/{total} completed", cls="text-sm text-gray-500 text-center")

    return app


# Create and run server
app = create_app(TodoApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
