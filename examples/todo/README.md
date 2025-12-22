# Todo App

A todo list application demonstrating Signal reactivity and Effect persistence.

## Run

```bash
uv run wtfui dev --web
# Open http://localhost:8000
```

## Patterns Demonstrated

| Pattern | Usage |
|---------|-------|
| **Signal[T]** | `_todos: Signal[list[Todo]]` for reactive state |
| **Effect** | `Effect(save_todos)` auto-saves on every change |
| **Context managers** | `with Flex(direction="row"):` for layout |
| **Event handlers** | `on_click=add_todo`, `on_change=...` |
| **Input binding** | `Input(bind=_new_todo_text)` for two-way binding |
| **@component** | Async component functions returning Element |

## Key Files

- `app.py` - Main application with TodoApp component
- `storage.py` - LocalStorage abstraction (JSON file persistence)

## Code Highlights

```python
# Reactive state
_todos: Signal[list[Todo]] = Signal([])

# Auto-persist on changes
Effect(save_todos)

# Context manager layout
with Flex(direction="row", gap=8):
    Input(bind=_new_todo_text, placeholder="What needs to be done?")
    Button(label="Add", on_click=add_todo)
```
