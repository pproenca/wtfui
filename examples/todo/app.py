# examples/todo/app.py
"""Todo App - Demonstrates Signal reactivity and context manager UI.

This example showcases:
- Signal[T] for reactive state
- Effect for side effects (persistence)
- Context manager UI (with VStack():)
- Event handlers (on_click, on_change)

Run with: uv run python examples/todo/app.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from flow import Effect, Element, Signal, component
from flow.server import create_app
from flow.ui import Button, HStack, Input, Text, VStack

from .storage import LocalStorage


@dataclass
class Todo:
    """A single todo item."""

    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    completed: bool = False


# Reactive state
todos: Signal[list[Todo]] = Signal([])
new_todo_text: Signal[str] = Signal("")

# Persistence
storage = LocalStorage()


def load_todos() -> None:
    """Load todos from storage."""
    data = storage.getItem("todos")
    if data:
        items = json.loads(data)
        todos.value = [Todo(**item) for item in items]


def save_todos() -> None:
    """Save todos to storage."""
    data = [{"id": t.id, "text": t.text, "completed": t.completed} for t in todos.value]
    storage.setItem("todos", json.dumps(data))


# Effect for persistence - runs on every todos change
Effect(save_todos)


def add_todo() -> None:
    """Add a new todo from input."""
    text = new_todo_text.value.strip()
    if text:
        todos.value = [*todos.value, Todo(text=text)]
        new_todo_text.value = ""


def toggle_todo(todo_id: str) -> None:
    """Toggle a todo's completed status."""
    todos.value = [
        Todo(
            id=t.id,
            text=t.text,
            completed=not t.completed if t.id == todo_id else t.completed,
        )
        for t in todos.value
    ]


def delete_todo(todo_id: str) -> None:
    """Delete a todo by ID."""
    todos.value = [t for t in todos.value if t.id != todo_id]


@component
async def TodoItem(todo: Todo) -> Element:
    """A single todo item component."""
    # Capture todo.id by value using default argument to avoid closure issues
    todo_id = todo.id

    with HStack(gap=8, align="center") as item:
        with Button(
            label="✓" if todo.completed else "○",
            on_click=lambda tid=todo_id: toggle_todo(tid),  # type: ignore[misc]
        ):
            pass
        with Text(todo.text, cls="line-through" if todo.completed else ""):
            pass
        with Button(label="x", on_click=lambda tid=todo_id: delete_todo(tid)):  # type: ignore[misc]
            pass
    return item


@component
async def TodoApp() -> Element:
    """Main todo application component."""
    # Load persisted todos on mount
    load_todos()

    with VStack(gap=16, padding=20) as app:
        with Text("Flow Todo App", cls="text-2xl font-bold"):
            pass

        # Input row
        with HStack(gap=8):
            with Input(
                bind=new_todo_text,
                placeholder="What needs to be done?",
                flex_grow=1,
            ):
                pass
            with Button(label="Add", on_click=add_todo):
                pass

        # Todo list
        with VStack(gap=4):
            for todo in todos.value:
                await TodoItem(todo)

        # Stats
        completed = len([t for t in todos.value if t.completed])
        total = len(todos.value)
        with Text(f"{completed}/{total} completed"):
            pass

    return app


# Create and run server
app = create_app(TodoApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
