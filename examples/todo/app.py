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

    # Neo-brutalist item styling with thick borders and offset shadows
    item_cls = (
        "group flex items-center gap-4 p-4 bg-zinc-900 border-2 border-zinc-700 w-full "
        "hover:border-lime-400 hover:translate-x-1 hover:-translate-y-1 "
        "hover:shadow-[4px_4px_0_0_#a3e635] transition-all duration-150"
    )
    if todo.completed:
        item_cls += " opacity-50"

    # Geometric checkbox with sharp corners
    check_cls = (
        "w-7 h-7 flex items-center justify-center border-2 transition-all duration-150 "
        "text-sm font-black"
    )
    if todo.completed:
        check_cls += " bg-lime-400 border-lime-400 text-zinc-900"
    else:
        check_cls += " border-zinc-600 text-zinc-600 hover:border-lime-400 hover:text-lime-400"

    # Text styling
    text_cls = "font-medium tracking-wide " + (
        "line-through text-zinc-600" if todo.completed else "text-zinc-100"
    )

    # Delete button - appears on hover
    delete_cls = (
        "w-7 h-7 flex items-center justify-center border-2 border-transparent "
        "text-zinc-600 hover:border-red-500 hover:text-red-500 hover:bg-red-500/10 "
        "transition-all duration-150 font-black text-sm"
    )

    with Flex(direction="row", cls=item_cls) as item:
        with Flex(direction="row", cls="shrink-0"):
            Button(
                label="✓" if todo.completed else "",
                on_click=lambda tid=todo_id: toggle_todo(tid),  # type: ignore[misc]
                cls=check_cls,
            )
        with Flex(direction="row", cls="grow min-w-0 ml-3"):
            Text(todo.text, cls=text_cls)
        with Flex(direction="row", cls="shrink-0 ml-auto"):
            Button(
                label="x",
                on_click=lambda tid=todo_id: delete_todo(tid),  # type: ignore[misc]
                cls=delete_cls,
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

    # Neo-brutalist dark theme with geometric accents
    with Flex(
        direction="column",
        cls=(
            "min-h-screen bg-zinc-950 py-16 px-4 "
            "bg-[radial-gradient(circle_at_20%_30%,rgba(163,230,53,0.03)_0%,transparent_50%)]"
        ),
    ) as app:
        # Main container with thick border and offset shadow
        with Flex(
            direction="column",
            cls=(
                "max-w-lg mx-auto bg-zinc-900 border-3 border-zinc-700 "
                "shadow-[8px_8px_0_0_#a3e635] p-8 space-y-8"
            ),
        ):
            # Header with bold typography
            with Flex(direction="column", cls="space-y-2"):
                with Flex(direction="row"):
                    Text(
                        "TASKS",
                        cls=("text-5xl font-black tracking-tighter text-zinc-100 leading-none"),
                    )
                with Flex(direction="row"):
                    Text(
                        "Get things done.",
                        cls="text-zinc-500 text-sm tracking-widest uppercase",
                    )

            # Decorative divider
            with Flex(direction="row", cls="h-1 w-full"):
                Flex(direction="row", cls="h-full w-1/3 bg-lime-400")
                Flex(direction="row", cls="h-full w-2/3 bg-zinc-800")

            # Input section with brutalist styling
            with Flex(direction="row", cls="gap-0"):
                Input(
                    bind=_new_todo_text,
                    placeholder="What needs to be done?",
                    cls=(
                        "flex-1 px-4 py-3 bg-zinc-800 border-2 border-zinc-700 "
                        "text-zinc-100 placeholder-zinc-500 "
                        "focus:outline-none focus:border-lime-400 transition-colors"
                    ),
                )
                Button(
                    label="ADD →",
                    on_click=add_todo,
                    cls=(
                        "px-6 py-3 bg-lime-400 text-zinc-900 font-black text-sm "
                        "tracking-wider border-2 border-lime-400 "
                        "hover:bg-lime-300 hover:shadow-[4px_4px_0_0_#3f3f46] "
                        "hover:translate-x-[-2px] hover:translate-y-[-2px] "
                        "active:translate-x-0 active:translate-y-0 active:shadow-none "
                        "transition-all duration-100"
                    ),
                )

            # Todo list with spacing
            with Flex(direction="column", cls="space-y-3"):
                for todo in _todos.value:
                    await TodoItem(todo)

                # Empty state
                if not _todos.value:
                    with Flex(
                        direction="column",
                        cls="py-12 items-center justify-center space-y-3",
                    ):
                        with Flex(direction="row"):
                            Text("□", cls="text-4xl text-zinc-700")
                        with Flex(direction="row"):
                            Text(
                                "No tasks yet",
                                cls="text-zinc-600 text-sm tracking-widest uppercase",
                            )

            # Stats bar
            completed = len([t for t in _todos.value if t.completed])
            total = len(_todos.value)

            with Flex(
                direction="row",
                cls="pt-6 border-t-2 border-zinc-800 items-center justify-between",
            ):
                with Flex(direction="row"):
                    Text(
                        f"{completed}/{total}",
                        cls="text-2xl font-black text-lime-400 tabular-nums",
                    )
                with Flex(direction="row"):
                    Text(
                        "COMPLETED",
                        cls="text-xs tracking-widest text-zinc-500",
                    )

    return app


# Create and run server
app = create_app(TodoApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
