# Dashboard Tutorial

Build a responsive dashboard demonstrating Flow's layout system and computed values.

## Concepts Covered

1. **Flex/Box Layout** - CSS Flexbox in Python
2. **Computed Values** - Lazy, cached derived state
3. **Responsive Sizing** - flex_grow for flexible layouts
4. **Component Composition** - Building from smaller parts

## Running the App

```bash
cd examples/dashboard
uv run python app.py
```

Open http://localhost:8001 in your browser.

## Code Walkthrough

### Flexbox Layout

Flow's layout mirrors CSS Flexbox exactly:

```python
from flow.ui import Flex, Box

# Full-height column layout
with Flex(direction="column", height="100vh"):
    # Fixed header
    with Box(height=60):
        Header()

    # Flexible body row
    with Flex(direction="row", flex_grow=1):
        # Fixed-width sidebar
        with Box(width=200):
            Sidebar()

        # Flexible main content
        with Flex(flex_grow=1):
            Content()
```

**Key properties:**
- `direction`: "row" | "column" | "row-reverse" | "column-reverse"
- `justify`: "flex-start" | "center" | "space-between" | "space-around"
- `align`: "flex-start" | "center" | "stretch" | "baseline"
- `gap`: spacing between children
- `flex_grow`: how much to grow (0 = fixed, 1+ = flexible)

### Computed Values

Computed values are lazy, cached, and auto-update:

```python
from flow import Signal, Computed

data = Signal([10, 20, 30])

@Computed
def total():
    return sum(data.value)

@Computed
def average():
    return total() / len(data.value)  # Chains work!

print(total())    # 60
data.value = [10, 20, 30, 40]
print(total())    # 100 - automatically recalculated
```

**Key differences from Effect:**
- Effect runs immediately and on every change
- Computed only runs when accessed (lazy)
- Computed caches result until dependencies change

### Fixed vs Flexible Sizing

```python
# FIXED: Always 200px wide
with Box(width=200):
    pass

# FLEXIBLE: Grows to fill available space
with Flex(flex_grow=1):
    pass

# FLEXIBLE with minimum
with Flex(flex_grow=1, min_width=300):
    pass
```

## Try It Yourself

1. **Add a chart** - Use a computed to transform data for visualization
2. **Add date range selector** - Filter data based on selected range
3. **Add responsive breakpoints** - Change layout based on screen size

## Vue Comparison

| Vue | Flow |
|-----|------|
| `computed: { total() {...} }` | `@Computed def total(): ...` |
| `<div class="flex">` | `with Flex():` |
| `:style="{ flexGrow: 1 }"` | `Flex(flex_grow=1)` |
