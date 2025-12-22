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
from wtfui.core.style import Colors, Style
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

    with Flex(direction="row", gap=8, align="center") as item:
        Button(
            label="✓" if todo.completed else "○",
            on_click=lambda tid=todo_id: toggle_todo(tid),  # type: ignore[misc]
        )
        Text(
            todo.text,
            style=Style(text_decoration="line-through", color=Colors.Slate._400)
            if todo.completed
            else None,
            flex_grow=1,
        )
        Button(
            label="x",
            on_click=lambda tid=todo_id: delete_todo(tid),  # type: ignore[misc]
            style=Style(color=Colors.Red._500),
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

    with Flex(direction="column", gap=16, padding=20) as app:
        Text("Flow Todo App", style=Style(font_size="2xl", font_weight="bold"))

        # Input row - horizontal flex
        with Flex(direction="row", gap=8, align="center"):
            Input(
                bind=_new_todo_text,
                placeholder="What needs to be done?",
                flex_grow=1,
            )
            Button(label="Add", on_click=add_todo)

        # Todo list - vertical flex
        with Flex(direction="column", gap=4):
            for todo in _todos.value:
                await TodoItem(todo)

        # Stats
        completed = len([t for t in _todos.value if t.completed])
        total = len(_todos.value)
        Text(f"{completed}/{total} completed", style=Style(color=Colors.Slate._500))

    return app


# Create and run server
app = create_app(TodoApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
