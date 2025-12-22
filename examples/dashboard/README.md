# Dashboard

An analytics dashboard demonstrating Computed values and Flexbox layout.

## Run

```bash
uv run wtfui dev --web
# Open http://localhost:8001
```

## Patterns Demonstrated

| Pattern | Usage |
|---------|-------|
| **Computed** | `@Computed def _total_sales()` for derived values |
| **Flexbox layout** | `Flex(direction="row", flex_grow=1)` |
| **Responsive sizing** | `wrap="wrap"` for responsive grids |
| **Component composition** | MetricCard, Sidebar as reusable components |
| **Style objects** | `Style(bg="white", rounded="lg", shadow="sm")` |

## Key Files

- `app.py` - Main Dashboard component
- `components/metric_card.py` - Reusable MetricCard component
- `components/sidebar.py` - Navigation sidebar component

## Code Highlights

```python
# Computed values auto-update when dependencies change
@Computed
def _total_sales() -> int:
    return sum(_sales_data.value)

# Flexbox with responsive wrap
with Flex(direction="row", gap=16, wrap="wrap"):
    await MetricCard(title="Total Sales", value=_total_sales)
    await MetricCard(title="Active Users", value=_user_count)
```
