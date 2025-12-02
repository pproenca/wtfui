# Todo App Tutorial

Learn Flow's core concepts by building a reactive todo application.

## Concepts Covered

1. **Signal[T]** - Observable state that notifies on change
2. **Effect** - Side effects that auto-track dependencies
3. **Context Manager UI** - `with VStack():` builds hierarchy
4. **Event Handlers** - `on_click`, `on_change` for interactivity

## Running the App

```bash
cd examples/todo
uv run python app.py
```

Open http://localhost:8000 in your browser.

## Code Walkthrough

### Reactive State with Signals

```python
from flow import Signal

# Create observable values
todos: Signal[list[Todo]] = Signal([])
new_todo_text: Signal[str] = Signal("")

# Read value
print(todos.value)  # []

# Write value - automatically notifies subscribers
todos.value = [Todo(text="Buy milk")]
```

**Key insight:** Unlike React's `useState`, you mutate `.value` directly. Flow detects the change and updates the UI.

### Side Effects with Effect

```python
from flow import Effect

# This function runs immediately, then re-runs whenever todos.value changes
Effect(save_todos)
```

**How it works:** When `save_todos()` reads `todos.value`, Flow tracks this dependency. Any future change to `todos.value` re-triggers the Effect.

### Context Manager UI

```python
from flow.ui import VStack, HStack, Button, Text

# Indentation = DOM hierarchy
with VStack(gap=16):           # Parent
    with Text("Title"):        # Child 1
        pass
    with HStack(gap=8):        # Child 2
        with Button(...):      # Grandchild
            pass
```

**Why context managers?** Python's `with` statement naturally expresses tree structure through indentation. No JSX, no templates - just Python.

### Event Handlers

```python
with Button(label="Add", on_click=add_todo):
    pass

with Input(bind=new_todo_text, on_change=lambda v: print(v)):
    pass
```

- `on_click`: Called when button is clicked
- `bind`: Two-way binding to a Signal
- `on_change`: Called with new value on input change

## Try It Yourself

1. **Add "Clear Completed" button** - Filter out completed todos
2. **Add filtering** - Show All/Active/Completed
3. **Add edit mode** - Double-click to edit todo text

## React Comparison

| React | Flow |
|-------|------|
| `const [todos, setTodos] = useState([])` | `todos = Signal([])` |
| `setTodos([...todos, item])` | `todos.value = [...todos.value, item]` |
| `useEffect(() => {...}, [todos])` | `Effect(fn)` (auto-tracks) |
| `<div><Child /></div>` | `with Div(): Child()` |
