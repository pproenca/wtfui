# Layout Engine

Yoga-compatible Flexbox implementation for computing element positions.

## Entry Point

`compute_layout(node, available)` in `compute.py` - main Flexbox algorithm:

```python
from wtfui.layout.compute import compute_layout
from wtfui.layout.types import Size

compute_layout(root_node, Size(800, 600))
# Results in root_node.layout (and all descendants)
```

## Algorithm Flow

1. **Resolve node size** - intrinsic, explicit, or available
2. **Apply aspect ratio** - if set, derive missing dimension
3. **Clamp to min/max** - enforce constraints
4. **Layout children** via `_layout_children()`:
   - Separate flex items from absolute/hidden
   - Collect into flex lines (`collect_flex_lines`)
   - Resolve flexible lengths (`resolve_flexible_lengths`)
   - Apply justify-content, align-items, align-content
   - Position absolutely-positioned children separately

## Layout Boundaries (No-GIL Parallelism)

A **Layout Boundary** has explicit width AND height - its layout doesn't depend on content size.

```python
node.is_layout_boundary()  # True if width + height both defined
```

**Parallel execution** (`parallel.py`):
- `compute_layout_parallel(node, available)` uses `ThreadPoolExecutor`
- After computing root + direct children, grandchildren subtrees run in parallel
- Threshold: `MIN_CHILDREN_FOR_PARALLEL = 3` (below this, sequential is faster)

```python
from wtfui.layout.parallel import compute_layout_parallel, find_layout_boundaries

# Find all parallelizable subtrees
boundaries = find_layout_boundaries(root)

# Parallel layout (uses No-GIL threads)
compute_layout_parallel(root, Size(800, 600))
```

## Intrinsic Sizing

`intrinsic.py` provides CSS intrinsic size functions:

| Function | Description |
|----------|-------------|
| `min-content` | Smallest width without overflow (widest word) |
| `max-content` | Ideal width without wrapping |
| `fit-content` | `min(max-content, max(min-content, available))` |

```python
from wtfui.layout.types import Dimension

style = FlexStyle(
    width=Dimension.min_content(),
    height=Dimension.fit_content(max_size=300),
)
```

For flex containers:
- **Row**: sum children's widths (min/max), max of heights
- **Column**: max of children's widths, sum heights

## FlexStyle Pattern

Frozen dataclass for thread safety (`style.py:161`):

```python
@dataclass(frozen=True, slots=True)
class FlexStyle:
    # Immutable - safe for No-GIL concurrent access
    flex_direction: FlexDirection = FlexDirection.ROW
    width: Dimension = field(default_factory=Dimension.auto)
    # ... 30+ properties
```

Update with `with_updates()`:
```python
new_style = style.with_updates(flex_grow=1.0, gap=10.0)
```

## Key Types

| Type | Location | Purpose |
|------|----------|---------|
| `LayoutNode` | `node.py` | Tree node with style, children, computed layout |
| `LayoutResult` | `node.py` | Computed x, y, width, height |
| `FlexStyle` | `style.py` | All Flexbox properties (frozen) |
| `Dimension` | `types.py` | auto/points/percent/intrinsic values |
| `Size` | `types.py` | width + height tuple |

## Module Map

- `compute.py` - Main entry point, Flexbox algorithm
- `parallel.py` - No-GIL parallel execution
- `algorithm.py` - Flex length resolution, alignment helpers
- `flexline.py` - Line collection and wrapping
- `intrinsic.py` - min/max/fit-content calculations
- `direction.py` - RTL/LTR direction resolution
- `cache.py` - Measurement caching for leaf nodes
- `baseline.py` - Text baseline alignment
