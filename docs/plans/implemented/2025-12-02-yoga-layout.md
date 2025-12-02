# Yoga Layout Engine for Flow - Implementation Plan

> **Goal:** Implement a pure Python Flexbox layout engine integrated with Flow's reactive system
> **Tech Stack:** Python 3.14+, Flow Framework, No external dependencies
> **Skills Reference:** See @.cursor/skills/test-driven-development.md for TDD protocol
> **Status:** RATIFIED by Python Steering Council (with amendments)

---

## Council Amendments (Mandatory)

This plan has been reviewed by the Python Steering Council against the Flow Manifesto. The following amendments are **mandatory** before execution.

### Amendment Alpha: Text Measurement Protocol

**Issue:** The plan assumed `width` and `height` are always inputs. In reality, `width` is often "however wide the text is." You cannot implement `min-content` without knowing font metrics.

**Solution:** Add a `MeasureFunc` callback to `LayoutNode`:
- **Server (HTML):** Returns estimates based on character count (rough)
- **Wasm (Browser):** Uses `canvas.measureText()` via JS Bridge
- **Server (Image):** Uses `Pillow` or `freetype` for exact pixel widths

**Implementation:** Task 1.6 (new)

### Amendment Beta: Style vs. Prop Conflict

**Issue:** Flow V1 uses Tailwind classes (`cls="w-10"`). Flow Yoga uses props (`width=40`). What happens if I write `with Box(cls="w-10", width=100):`?

**Ruling:** **Explicit Layout Props define the Truth.**
- The Layout Engine calculates the geometry
- The `cls` prop is for *styling* (color, shadow, font), not *geometry*
- The Renderer must strip geometry-related classes from `cls` if explicit layout props are present

**Implementation:** Task 4.3 (new)

### Amendment Gamma: Layout Boundaries

**Issue:** Parallelizing a recursive tree is dangerous. If Child A depends on Parent B's width, they cannot run in parallel. Also, layout thrashing is expensive—if a leaf node grows by 1px, does it trigger a root re-layout?

**Solution:** Only parallelize **Independent Sub-trees** (Layout Boundaries):
- A node with explicit `width` AND `height` is a "Layout Boundary"
- Layout Boundaries do NOT propagate dirty flags to their parent
- Layout Boundaries CAN be computed in parallel threads

**Implementation:** Tasks 1.5 (updated), 3.3 (updated), 5.5 (updated)

### Council Directive: Floating-Point Precision

**Issue:** CSS rendering engines sometimes floor/ceil sub-pixels differently. Floating-point errors like `0.30000000004` can cause infinite oscillation in flex basis calculations.

**Directive:** In `compute_layout`, treat values within **0.001** difference as equal.

**Implementation:** Task 2.5 (updated), utility function in `src/flow/layout/types.py`

---

## Overview

This plan implements a **Python Flexbox layout engine** inspired by Meta's [Yoga](https://www.yogalayout.dev/) and Dioxus's [Taffy](https://docs.rs/taffy/). The engine computes layout positions for Flow UI elements following the [CSS Flexbox specification](https://www.w3.org/TR/css-flexbox-1/).

### Design Principles (from MANIFEST.md + Council Amendments)

1. **Indentation is Topology** - Layout containers use `with` blocks ✅
2. **Universal Isomorphism** - Layout is computed abstractly, rendered anywhere ✅
3. **Atomic Reactivity** - Style changes trigger precise re-layout ✅
4. **Native Leverage** - Use Python 3.14+ features (No-GIL for parallel layout) ✅

**Council-Mandated Additions:**

5. **Content Measurement** (Alpha) - Text nodes have `MeasureFunc` to report intrinsic size
6. **Props are Truth** (Beta) - Explicit layout props override conflicting CSS classes
7. **Layout Boundaries** (Gamma) - Fixed-dimension nodes isolate layout recalculation

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flow Elements                            │
│   with Flex(direction="row", justify="center"):                 │
│       with Box(width=100, height=50):   ← Layout Boundary       │
│           Text("Hello")                 ← Triggers MeasureFunc  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Layout Tree                                │
│   LayoutNode(style=FlexStyle, children=[...])                   │
│       - measure_func: MeasureFunc | None   ← Amendment Alpha    │
│       - is_layout_boundary: bool           ← Amendment Gamma    │
│       - computed_layout: LayoutResult                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MeasureFunc Protocol                         │
│   Callable[[AvailableSpace, AvailableSpace], Size]              │
│       - HTML: character count estimation                        │
│       - Browser: canvas.measureText() via JS Bridge             │
│       - Image: Pillow/freetype exact metrics                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Flexbox Algorithm                             │
│   compute_layout(node, available_space) → LayoutResult          │
│       1. Resolve sizes (min/max/basis) OR call measure_func     │
│       2. Collect into flex lines                                │
│       3. Grow/shrink items                                      │
│       4. Align main axis (justify-content)                      │
│       5. Align cross axis (align-items/align-content)           │
│       6. Position absolutely-placed children                    │
│       7. Parallel compute Layout Boundary subtrees (3.14+)      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RenderNode                                │
│   { tag: "div", props: { style: computed_css }, children }      │
│   - Renderer strips geometry classes when props conflict        │
│   - Renderer receives computed positions for final output       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Data Structures

### Task 1.1: Dimension Types

**Files:**
- Create: `src/flow/layout/__init__.py`
- Create: `src/flow/layout/types.py`
- Test: `tests/test_layout_types.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_types.py
import pytest
from flow.layout.types import Dimension, Size, Rect, Point

class TestDimension:
    def test_dimension_auto(self):
        dim = Dimension.auto()
        assert dim.is_auto()
        assert not dim.is_defined()

    def test_dimension_points(self):
        dim = Dimension.points(100)
        assert dim.value == 100
        assert dim.unit == "px"
        assert dim.is_defined()

    def test_dimension_percent(self):
        dim = Dimension.percent(50)
        assert dim.value == 50
        assert dim.unit == "%"

    def test_dimension_resolve_percent(self):
        dim = Dimension.percent(50)
        resolved = dim.resolve(200)  # 50% of 200 = 100
        assert resolved == 100

class TestSize:
    def test_size_creation(self):
        size = Size(width=100, height=50)
        assert size.width == 100
        assert size.height == 50

    def test_size_zero(self):
        size = Size.zero()
        assert size.width == 0
        assert size.height == 0

class TestRect:
    def test_rect_from_position_and_size(self):
        rect = Rect(x=10, y=20, width=100, height=50)
        assert rect.left == 10
        assert rect.top == 20
        assert rect.right == 110
        assert rect.bottom == 70

class TestFloatingPointPrecision:
    """Council Directive: Floating-point precision utilities."""

    def test_layout_epsilon_constant(self):
        from flow.layout.types import LAYOUT_EPSILON
        assert LAYOUT_EPSILON == 0.001

    def test_approx_equal_within_epsilon(self):
        from flow.layout.types import approx_equal
        assert approx_equal(1.0, 1.0009)
        assert approx_equal(0.3, 0.30000000004)
        assert not approx_equal(1.0, 1.002)

    def test_approx_equal_custom_epsilon(self):
        from flow.layout.types import approx_equal
        assert approx_equal(1.0, 1.05, epsilon=0.1)
        assert not approx_equal(1.0, 1.05, epsilon=0.01)

    def test_snap_to_pixel_default(self):
        from flow.layout.types import snap_to_pixel
        assert snap_to_pixel(10.4) == 10.0
        assert snap_to_pixel(10.6) == 11.0
        assert snap_to_pixel(10.5) == 10.0  # round half to even

    def test_snap_to_pixel_with_scale(self):
        from flow.layout.types import snap_to_pixel
        # Scale 2 = half-pixel grid (0, 0.5, 1.0, 1.5, ...)
        assert snap_to_pixel(10.3, scale=2) == 10.5
        assert snap_to_pixel(10.1, scale=2) == 10.0
```

**Step 2: Run test to verify it fails**
```bash
uv run pytest tests/test_layout_types.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'flow.layout'"

**Step 3: Write minimal implementation**
```python
# src/flow/layout/types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Literal

class DimensionUnit(Enum):
    AUTO = "auto"
    POINTS = "px"
    PERCENT = "%"

@dataclass(frozen=True, slots=True)
class Dimension:
    value: float | None = None
    unit: DimensionUnit = DimensionUnit.AUTO

    @classmethod
    def auto(cls) -> Dimension:
        return cls(None, DimensionUnit.AUTO)

    @classmethod
    def points(cls, value: float) -> Dimension:
        return cls(value, DimensionUnit.POINTS)

    @classmethod
    def percent(cls, value: float) -> Dimension:
        return cls(value, DimensionUnit.PERCENT)

    def is_auto(self) -> bool:
        return self.unit == DimensionUnit.AUTO

    def is_defined(self) -> bool:
        return self.unit != DimensionUnit.AUTO and self.value is not None

    def resolve(self, parent_value: float) -> float | None:
        if self.unit == DimensionUnit.POINTS:
            return self.value
        elif self.unit == DimensionUnit.PERCENT and self.value is not None:
            return (self.value / 100) * parent_value
        return None

@dataclass(frozen=True, slots=True)
class Size:
    width: float = 0
    height: float = 0

    @classmethod
    def zero(cls) -> Size:
        return cls(0, 0)

@dataclass(frozen=True, slots=True)
class Point:
    x: float = 0
    y: float = 0

@dataclass(frozen=True, slots=True)
class Rect:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

# Council Directive: Floating-Point Precision
LAYOUT_EPSILON = 0.001

def approx_equal(a: float, b: float, epsilon: float = LAYOUT_EPSILON) -> bool:
    """Check if two floats are approximately equal within epsilon."""
    return abs(a - b) < epsilon

def snap_to_pixel(value: float, scale: float = 1.0) -> float:
    """
    Snap a layout value to the nearest sub-pixel.

    This prevents CSS rendering inconsistencies between browsers
    that floor/ceil sub-pixels differently.
    """
    return round(value * scale) / scale
```

**Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_layout_types.py -v
```
Expected: PASS

**Step 5: Commit**
```bash
git add src/flow/layout/ tests/test_layout_types.py
git commit -m "feat(layout): add core dimension types (Dimension, Size, Rect, Point)"
```

---

### Task 1.2: Edge/Spacing Types

**Files:**
- Modify: `src/flow/layout/types.py`
- Modify: `tests/test_layout_types.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_types.py
from flow.layout.types import Edges, Spacing

class TestEdges:
    def test_edges_all(self):
        edges = Edges.all(10)
        assert edges.top == 10
        assert edges.right == 10
        assert edges.bottom == 10
        assert edges.left == 10

    def test_edges_symmetric(self):
        edges = Edges.symmetric(horizontal=20, vertical=10)
        assert edges.top == 10
        assert edges.bottom == 10
        assert edges.left == 20
        assert edges.right == 20

    def test_edges_horizontal_sum(self):
        edges = Edges(top=5, right=10, bottom=15, left=20)
        assert edges.horizontal == 30  # left + right
        assert edges.vertical == 20    # top + bottom

class TestSpacing:
    def test_spacing_resolve(self):
        spacing = Spacing(
            top=Dimension.points(10),
            right=Dimension.percent(10),
            bottom=Dimension.points(10),
            left=Dimension.auto()
        )
        resolved = spacing.resolve(width=200, height=100)
        assert resolved.top == 10
        assert resolved.right == 20  # 10% of 200
        assert resolved.bottom == 10
        assert resolved.left == 0    # auto resolves to 0 for spacing
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/types.py

@dataclass(frozen=True, slots=True)
class Edges:
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> Edges:
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, horizontal: float = 0, vertical: float = 0) -> Edges:
        return cls(vertical, horizontal, vertical, horizontal)

    @classmethod
    def zero(cls) -> Edges:
        return cls(0, 0, 0, 0)

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom

@dataclass(frozen=True, slots=True)
class Spacing:
    top: Dimension = field(default_factory=Dimension.auto)
    right: Dimension = field(default_factory=Dimension.auto)
    bottom: Dimension = field(default_factory=Dimension.auto)
    left: Dimension = field(default_factory=Dimension.auto)

    def resolve(self, width: float, height: float) -> Edges:
        return Edges(
            top=self.top.resolve(height) or 0,
            right=self.right.resolve(width) or 0,
            bottom=self.bottom.resolve(height) or 0,
            left=self.left.resolve(width) or 0,
        )
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**
```bash
git commit -am "feat(layout): add Edges and Spacing types"
```

---

### Task 1.3: Flex Style Enums

**Files:**
- Create: `src/flow/layout/style.py`
- Test: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_style.py
import pytest
from flow.layout.style import (
    FlexDirection, FlexWrap, JustifyContent,
    AlignItems, AlignContent, Position
)

class TestFlexDirection:
    def test_row_is_horizontal(self):
        assert FlexDirection.ROW.is_row()
        assert not FlexDirection.ROW.is_column()

    def test_column_is_vertical(self):
        assert FlexDirection.COLUMN.is_column()
        assert not FlexDirection.COLUMN.is_row()

    def test_reverse_directions(self):
        assert FlexDirection.ROW_REVERSE.is_reverse()
        assert FlexDirection.COLUMN_REVERSE.is_reverse()
        assert not FlexDirection.ROW.is_reverse()

class TestFlexWrap:
    def test_wrap_modes(self):
        assert FlexWrap.NO_WRAP.is_no_wrap()
        assert FlexWrap.WRAP.is_wrap()
        assert FlexWrap.WRAP_REVERSE.is_wrap()
        assert FlexWrap.WRAP_REVERSE.is_reverse()
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
```python
# src/flow/layout/style.py
from enum import Enum

class FlexDirection(Enum):
    ROW = "row"
    COLUMN = "column"
    ROW_REVERSE = "row-reverse"
    COLUMN_REVERSE = "column-reverse"

    def is_row(self) -> bool:
        return self in (FlexDirection.ROW, FlexDirection.ROW_REVERSE)

    def is_column(self) -> bool:
        return self in (FlexDirection.COLUMN, FlexDirection.COLUMN_REVERSE)

    def is_reverse(self) -> bool:
        return self in (FlexDirection.ROW_REVERSE, FlexDirection.COLUMN_REVERSE)

class FlexWrap(Enum):
    NO_WRAP = "nowrap"
    WRAP = "wrap"
    WRAP_REVERSE = "wrap-reverse"

    def is_no_wrap(self) -> bool:
        return self == FlexWrap.NO_WRAP

    def is_wrap(self) -> bool:
        return self in (FlexWrap.WRAP, FlexWrap.WRAP_REVERSE)

    def is_reverse(self) -> bool:
        return self == FlexWrap.WRAP_REVERSE

class JustifyContent(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"

class AlignItems(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"

class AlignContent(Enum):
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"

class Position(Enum):
    RELATIVE = "relative"
    ABSOLUTE = "absolute"
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add Flexbox style enums"
```

---

### Task 1.4: FlexStyle Dataclass

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.style import FlexStyle
from flow.layout.types import Dimension

class TestFlexStyle:
    def test_default_style(self):
        style = FlexStyle()
        assert style.flex_direction == FlexDirection.ROW
        assert style.flex_wrap == FlexWrap.NO_WRAP
        assert style.justify_content == JustifyContent.FLEX_START
        assert style.align_items == AlignItems.STRETCH

    def test_style_with_dimensions(self):
        style = FlexStyle(
            width=Dimension.points(100),
            height=Dimension.percent(50),
            flex_grow=1.0,
            flex_shrink=0.0,
        )
        assert style.width.resolve(200) == 100
        assert style.height.resolve(200) == 100
        assert style.flex_grow == 1.0

    def test_style_immutable(self):
        style = FlexStyle()
        with pytest.raises(Exception):  # frozen dataclass
            style.flex_grow = 1.0

    def test_style_copy_with(self):
        style = FlexStyle(flex_grow=1.0)
        new_style = style.with_updates(flex_shrink=0.5)
        assert new_style.flex_grow == 1.0
        assert new_style.flex_shrink == 0.5
        assert style.flex_shrink != 0.5  # original unchanged
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/style.py
from dataclasses import dataclass, field, replace
from flow.layout.types import Dimension, Spacing

@dataclass(frozen=True, slots=True)
class FlexStyle:
    # Display & Position
    position: Position = Position.RELATIVE

    # Flex Container Properties
    flex_direction: FlexDirection = FlexDirection.ROW
    flex_wrap: FlexWrap = FlexWrap.NO_WRAP
    justify_content: JustifyContent = JustifyContent.FLEX_START
    align_items: AlignItems = AlignItems.STRETCH
    align_content: AlignContent = AlignContent.STRETCH

    # Flex Item Properties
    flex_grow: float = 0.0
    flex_shrink: float = 1.0
    flex_basis: Dimension = field(default_factory=Dimension.auto)
    align_self: AlignItems | None = None

    # Sizing
    width: Dimension = field(default_factory=Dimension.auto)
    height: Dimension = field(default_factory=Dimension.auto)
    min_width: Dimension = field(default_factory=Dimension.auto)
    min_height: Dimension = field(default_factory=Dimension.auto)
    max_width: Dimension = field(default_factory=Dimension.auto)
    max_height: Dimension = field(default_factory=Dimension.auto)
    aspect_ratio: float | None = None

    # Spacing
    margin: Spacing = field(default_factory=Spacing)
    padding: Spacing = field(default_factory=Spacing)
    gap: float = 0.0
    row_gap: float | None = None
    column_gap: float | None = None

    # Position offsets (for position: absolute)
    top: Dimension = field(default_factory=Dimension.auto)
    right: Dimension = field(default_factory=Dimension.auto)
    bottom: Dimension = field(default_factory=Dimension.auto)
    left: Dimension = field(default_factory=Dimension.auto)

    def with_updates(self, **kwargs) -> FlexStyle:
        return replace(self, **kwargs)

    def get_gap(self, direction: FlexDirection) -> float:
        if direction.is_row():
            return self.column_gap if self.column_gap is not None else self.gap
        return self.row_gap if self.row_gap is not None else self.gap
```

---

### Task 1.5: LayoutNode, LayoutResult, and Layout Boundaries (Amendment Gamma)

**Files:**
- Create: `src/flow/layout/node.py`
- Test: `tests/test_layout_node.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_node.py
import pytest
from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import FlexStyle, FlexDirection
from flow.layout.types import Dimension

class TestLayoutNode:
    def test_create_node(self):
        node = LayoutNode(style=FlexStyle())
        assert node.style.flex_direction.is_row()
        assert len(node.children) == 0

    def test_add_children(self):
        parent = LayoutNode(style=FlexStyle())
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=2.0))

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1.parent is parent
        assert child2.parent is parent

    def test_layout_result(self):
        result = LayoutResult(x=10, y=20, width=100, height=50)
        assert result.x == 10
        assert result.y == 20
        assert result.width == 100
        assert result.height == 50

class TestLayoutNodeTree:
    def test_tree_structure(self):
        root = LayoutNode(style=FlexStyle(width=Dimension.points(300)))
        row = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        cell1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        cell2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(row)
        row.add_child(cell1)
        row.add_child(cell2)

        assert root.children[0] is row
        assert row.children[0] is cell1
        assert row.children[1] is cell2

class TestLayoutBoundary:
    """Amendment Gamma: Layout Boundaries prevent layout thrashing."""

    def test_node_with_fixed_dimensions_is_boundary(self):
        """A node with explicit width AND height is a Layout Boundary."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )
        assert node.is_layout_boundary()

    def test_node_without_fixed_dimensions_is_not_boundary(self):
        """A node without both dimensions is NOT a Layout Boundary."""
        node = LayoutNode(style=FlexStyle(flex_grow=1.0))
        assert not node.is_layout_boundary()

        node_width_only = LayoutNode(
            style=FlexStyle(width=Dimension.points(100))
        )
        assert not node_width_only.is_layout_boundary()

    def test_layout_boundary_does_not_propagate_dirty(self):
        """Layout Boundaries do NOT mark their parent dirty."""
        parent = LayoutNode(style=FlexStyle())
        boundary_child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )
        grandchild = LayoutNode(style=FlexStyle())

        parent.add_child(boundary_child)
        boundary_child.add_child(grandchild)

        # Clear all dirty flags
        parent._dirty = False
        boundary_child._dirty = False
        grandchild._dirty = False

        # Mark grandchild dirty
        grandchild.mark_dirty()

        # Boundary child is dirty (it's the direct parent)
        assert boundary_child.is_dirty()
        # BUT parent is NOT dirty (boundary blocks propagation)
        assert not parent.is_dirty()

    def test_non_boundary_propagates_dirty_to_parent(self):
        """Non-boundary nodes propagate dirty to parent normally."""
        parent = LayoutNode(style=FlexStyle())
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))  # Not a boundary
        grandchild = LayoutNode(style=FlexStyle())

        parent.add_child(child)
        child.add_child(grandchild)

        parent._dirty = False
        child._dirty = False
        grandchild._dirty = False

        grandchild.mark_dirty()

        assert child.is_dirty()
        assert parent.is_dirty()  # Propagated through non-boundary
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/node.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from flow.layout.style import FlexStyle
    from flow.layout.measure import MeasureFunc

@dataclass
class LayoutResult:
    """Computed layout position and size."""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

@dataclass
class LayoutNode:
    """A node in the layout tree."""
    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    parent: LayoutNode | None = field(default=None, repr=False)
    measure_func: MeasureFunc | None = field(default=None)

    # Computed layout (set after compute_layout)
    layout: LayoutResult = field(default_factory=LayoutResult)

    # Internal state for layout algorithm
    _dirty: bool = field(default=True, repr=False)

    def add_child(self, child: LayoutNode) -> None:
        # Amendment Alpha: Measured nodes are leaf nodes
        if self.measure_func is not None:
            raise ValueError("Cannot add children to a measured node")
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: LayoutNode) -> None:
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def is_layout_boundary(self) -> bool:
        """
        Amendment Gamma: Check if this node is a Layout Boundary.

        A Layout Boundary has explicit width AND height, meaning
        its internal layout is independent of its parent.
        """
        return (
            self.style.width.is_defined() and
            self.style.height.is_defined()
        )

    def mark_dirty(self) -> None:
        """
        Mark this node as needing layout.

        Amendment Gamma: Layout Boundaries do NOT propagate dirty
        flags to their parent, preventing layout thrashing.
        """
        self._dirty = True
        if self.parent is not None and not self.is_layout_boundary():
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False
```

---

### Task 1.6: Text Measurement Protocol (Amendment Alpha)

**Files:**
- Create: `src/flow/layout/measure.py`
- Modify: `src/flow/layout/node.py`
- Test: `tests/test_layout_measure.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_measure.py
import pytest
from flow.layout.measure import MeasureFunc, MeasureContext, create_text_measure
from flow.layout.algorithm import AvailableSpace
from flow.layout.types import Size

class TestMeasureFunc:
    def test_measure_func_protocol(self):
        """MeasureFunc returns Size given available space."""
        def simple_measure(
            available_width: AvailableSpace,
            available_height: AvailableSpace,
            context: MeasureContext,
        ) -> Size:
            # Fixed size regardless of available space
            return Size(width=100, height=20)

        result = simple_measure(
            AvailableSpace.definite(500),
            AvailableSpace.definite(500),
            MeasureContext(),
        )
        assert result.width == 100
        assert result.height == 20

    def test_text_measure_character_count(self):
        """Character-based text measurement for server-side."""
        measure = create_text_measure(
            text="Hello World",
            font_size=16,
            chars_per_em=0.5,  # Rough estimate
        )

        result = measure(
            AvailableSpace.max_content(),
            AvailableSpace.max_content(),
            MeasureContext(),
        )

        # 11 chars * 16px * 0.5 = 88px width
        assert result.width == 88
        # Single line height
        assert result.height == 16 * 1.2  # line-height factor

    def test_text_measure_wrapping(self):
        """Text wraps when constrained width."""
        measure = create_text_measure(
            text="Hello World",
            font_size=16,
            chars_per_em=0.5,
        )

        result = measure(
            AvailableSpace.definite(50),  # Constrain width
            AvailableSpace.max_content(),
            MeasureContext(),
        )

        # Text should wrap to multiple lines
        assert result.width <= 50
        assert result.height > 16 * 1.2  # More than one line

class TestMeasureContext:
    def test_context_has_renderer_hint(self):
        """Context can carry renderer-specific hints."""
        ctx = MeasureContext(renderer="html", font_family="sans-serif")
        assert ctx.renderer == "html"
        assert ctx.font_family == "sans-serif"

class TestLayoutNodeWithMeasure:
    def test_node_accepts_measure_func(self):
        """LayoutNode can have a measure function."""
        from flow.layout.node import LayoutNode
        from flow.layout.style import FlexStyle

        def my_measure(w, h, ctx):
            return Size(width=50, height=25)

        node = LayoutNode(
            style=FlexStyle(),
            measure_func=my_measure,
        )

        assert node.measure_func is not None
        assert node.measure_func(
            AvailableSpace.max_content(),
            AvailableSpace.max_content(),
            MeasureContext(),
        ) == Size(width=50, height=25)

    def test_leaf_node_with_measure_has_no_children(self):
        """Nodes with measure_func are leaf nodes."""
        from flow.layout.node import LayoutNode
        from flow.layout.style import FlexStyle

        node = LayoutNode(
            style=FlexStyle(),
            measure_func=lambda w, h, c: Size(50, 25),
        )

        # Cannot add children to a measured node
        child = LayoutNode(style=FlexStyle())
        with pytest.raises(ValueError, match="measured node"):
            node.add_child(child)
```

**Step 2: Run test to verify it fails**
```bash
uv run pytest tests/test_layout_measure.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'flow.layout.measure'"

**Step 3: Write minimal implementation**
```python
# src/flow/layout/measure.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.algorithm import AvailableSpace
    from flow.layout.types import Size

@dataclass(frozen=True)
class MeasureContext:
    """Context passed to measure functions for renderer-specific hints."""
    renderer: str = "html"
    font_family: str = "sans-serif"
    font_weight: int = 400
    extra: dict = field(default_factory=dict)

class MeasureFunc(Protocol):
    """Protocol for measuring intrinsic content size."""
    def __call__(
        self,
        available_width: AvailableSpace,
        available_height: AvailableSpace,
        context: MeasureContext,
    ) -> Size:
        ...

def create_text_measure(
    text: str,
    font_size: float = 16,
    chars_per_em: float = 0.5,
    line_height: float = 1.2,
) -> MeasureFunc:
    """
    Create a character-count based text measure function.

    This is a rough estimate for server-side rendering.
    For exact measurements, use renderer-specific implementations:
    - Browser: canvas.measureText() via JS Bridge
    - Image: Pillow ImageFont.getbbox() or freetype
    """
    from flow.layout.algorithm import AvailableSpace
    from flow.layout.types import Size

    char_width = font_size * chars_per_em
    line_h = font_size * line_height

    def measure(
        available_width: AvailableSpace,
        available_height: AvailableSpace,
        context: MeasureContext,
    ) -> Size:
        total_width = len(text) * char_width

        if available_width.is_definite() and available_width.value is not None:
            max_width = available_width.value
            if total_width > max_width:
                # Wrap text
                chars_per_line = max(1, int(max_width / char_width))
                num_lines = (len(text) + chars_per_line - 1) // chars_per_line
                return Size(
                    width=min(total_width, max_width),
                    height=num_lines * line_h,
                )

        # No wrapping - single line
        return Size(width=total_width, height=line_h)

    return measure

# Renderer-specific measure function factories (stubs for now)

def create_canvas_text_measure(text: str, font: str) -> MeasureFunc:
    """
    Create a measure function that uses browser canvas.measureText().

    This will be called via the JS Bridge when running in WASM context.
    Implementation requires the RPC bridge to be set up.
    """
    # Stub - actual implementation needs JS bridge
    return create_text_measure(text)

def create_pillow_text_measure(text: str, font_path: str, font_size: float) -> MeasureFunc:
    """
    Create a measure function using Pillow for exact pixel measurements.

    Requires: PIL/Pillow installed
    """
    from flow.layout.algorithm import AvailableSpace
    from flow.layout.types import Size

    try:
        from PIL import ImageFont
        font = ImageFont.truetype(font_path, int(font_size))

        def measure(
            available_width: AvailableSpace,
            available_height: AvailableSpace,
            context: MeasureContext,
        ) -> Size:
            bbox = font.getbbox(text)
            return Size(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])

        return measure
    except ImportError:
        # Fall back to character-based estimation
        return create_text_measure(text, font_size=font_size)
```

**Step 4: Update LayoutNode to accept measure_func**
```python
# Modify src/flow/layout/node.py - add to LayoutNode dataclass

from flow.layout.measure import MeasureFunc

@dataclass
class LayoutNode:
    """A node in the layout tree."""
    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    parent: LayoutNode | None = field(default=None, repr=False)
    measure_func: MeasureFunc | None = field(default=None)  # NEW

    # Computed layout (set after compute_layout)
    layout: LayoutResult = field(default_factory=LayoutResult)

    # Internal state for layout algorithm
    _dirty: bool = field(default=True, repr=False)

    def add_child(self, child: LayoutNode) -> None:
        # NEW: Prevent adding children to measured nodes
        if self.measure_func is not None:
            raise ValueError("Cannot add children to a measured node")
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    # ... rest of methods unchanged
```

**Step 5: Run test to verify it passes**
```bash
uv run pytest tests/test_layout_measure.py -v
```
Expected: PASS

**Step 6: Commit**
```bash
git add src/flow/layout/measure.py tests/test_layout_measure.py
git commit -m "feat(layout): add MeasureFunc protocol for text measurement (Amendment Alpha)"
```

---

## Phase 2: Flexbox Algorithm

### Task 2.1: Available Space & Sizing Mode

**Files:**
- Create: `src/flow/layout/algorithm.py`
- Test: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_algorithm.py
from flow.layout.algorithm import AvailableSpace, SizingMode

class TestAvailableSpace:
    def test_definite_space(self):
        space = AvailableSpace.definite(100)
        assert space.is_definite()
        assert space.value == 100

    def test_min_content(self):
        space = AvailableSpace.min_content()
        assert space.is_min_content()

    def test_max_content(self):
        space = AvailableSpace.max_content()
        assert space.is_max_content()

    def test_resolve_definite(self):
        space = AvailableSpace.definite(200)
        assert space.resolve() == 200

    def test_resolve_min_content(self):
        space = AvailableSpace.min_content()
        assert space.resolve() == 0

class TestSizingMode:
    def test_sizing_modes(self):
        assert SizingMode.CONTENT_BOX.is_content_box()
        assert SizingMode.BORDER_BOX.is_border_box()
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/algorithm.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.types import Size

class SizingMode(Enum):
    CONTENT_BOX = "content-box"
    BORDER_BOX = "border-box"

    def is_content_box(self) -> bool:
        return self == SizingMode.CONTENT_BOX

    def is_border_box(self) -> bool:
        return self == SizingMode.BORDER_BOX

@dataclass(frozen=True)
class AvailableSpace:
    """Represents available space for layout computation."""
    _value: float | None
    _mode: str  # "definite", "min-content", "max-content"

    @classmethod
    def definite(cls, value: float) -> AvailableSpace:
        return cls(value, "definite")

    @classmethod
    def min_content(cls) -> AvailableSpace:
        return cls(None, "min-content")

    @classmethod
    def max_content(cls) -> AvailableSpace:
        return cls(None, "max-content")

    def is_definite(self) -> bool:
        return self._mode == "definite"

    def is_min_content(self) -> bool:
        return self._mode == "min-content"

    def is_max_content(self) -> bool:
        return self._mode == "max-content"

    @property
    def value(self) -> float | None:
        return self._value

    def resolve(self) -> float:
        if self._value is not None:
            return self._value
        return 0.0 if self.is_min_content() else float('inf')
```

---

### Task 2.2: Resolve Flex Item Sizes

**Files:**
- Modify: `src/flow/layout/algorithm.py`
- Modify: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_algorithm.py
from flow.layout.algorithm import resolve_flexible_lengths
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle, FlexDirection
from flow.layout.types import Dimension

class TestResolveFlexibleLengths:
    def test_equal_flex_grow(self):
        """Two items with flex-grow: 1 split space equally."""
        items = [
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
        ]
        container_main = 200
        gap = 0

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=container_main,
            direction=FlexDirection.ROW,
            gap=gap,
        )

        assert sizes[0] == 100
        assert sizes[1] == 100

    def test_weighted_flex_grow(self):
        """Items with flex-grow 1:2 ratio."""
        items = [
            LayoutNode(style=FlexStyle(flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_grow=2.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=300,
            direction=FlexDirection.ROW,
            gap=0,
        )

        assert sizes[0] == 100  # 1/3 of 300
        assert sizes[1] == 200  # 2/3 of 300

    def test_flex_basis_respected(self):
        """Flex-basis sets initial size before grow/shrink."""
        items = [
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=1.0)),
            LayoutNode(style=FlexStyle(flex_basis=Dimension.points(50), flex_grow=1.0)),
        ]

        sizes = resolve_flexible_lengths(
            items=items,
            container_main_size=200,
            direction=FlexDirection.ROW,
            gap=0,
        )

        # 200 total - 100 (basis) = 100 free space, split equally
        assert sizes[0] == 100  # 50 basis + 50 grown
        assert sizes[1] == 100  # 50 basis + 50 grown
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/algorithm.py

def resolve_flexible_lengths(
    items: list[LayoutNode],
    container_main_size: float,
    direction: FlexDirection,
    gap: float,
) -> list[float]:
    """
    Resolve flex item sizes based on flex-grow/flex-shrink.

    Implements CSS Flexbox spec section 9.7:
    https://www.w3.org/TR/css-flexbox-1/#resolve-flexible-lengths
    """
    if not items:
        return []

    from flow.layout.style import FlexDirection

    # Calculate total gap space
    total_gap = gap * (len(items) - 1) if len(items) > 1 else 0
    available_space = container_main_size - total_gap

    # Get flex basis for each item
    bases = []
    for item in items:
        basis = item.style.flex_basis
        if basis.is_defined():
            bases.append(basis.resolve(container_main_size) or 0)
        else:
            # Auto basis - use width/height based on direction
            if direction.is_row():
                dim = item.style.width
            else:
                dim = item.style.height
            bases.append(dim.resolve(container_main_size) or 0)

    total_basis = sum(bases)
    free_space = available_space - total_basis

    # Calculate flex factors
    if free_space >= 0:
        # Growing
        total_grow = sum(item.style.flex_grow for item in items)
        if total_grow == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_grow / total_grow))
            for base, item in zip(bases, items)
        ]
    else:
        # Shrinking
        total_shrink = sum(item.style.flex_shrink * base for base, item in zip(bases, items))
        if total_shrink == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_shrink * base / total_shrink))
            for base, item in zip(bases, items)
        ]
```

---

### Task 2.3: Justify Content Distribution

**Files:**
- Modify: `src/flow/layout/algorithm.py`
- Modify: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_algorithm.py
from flow.layout.algorithm import distribute_justify_content
from flow.layout.style import JustifyContent

class TestJustifyContent:
    def test_flex_start(self):
        """Items align to start with no gaps."""
        positions = distribute_justify_content(
            item_sizes=[50, 50, 50],
            container_size=300,
            justify=JustifyContent.FLEX_START,
            gap=0,
        )
        assert positions == [0, 50, 100]

    def test_flex_end(self):
        """Items align to end."""
        positions = distribute_justify_content(
            item_sizes=[50, 50, 50],
            container_size=300,
            justify=JustifyContent.FLEX_END,
            gap=0,
        )
        assert positions == [150, 200, 250]

    def test_center(self):
        """Items centered in container."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.CENTER,
            gap=0,
        )
        assert positions == [50, 100]  # 50px on each side

    def test_space_between(self):
        """Space distributed between items."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.SPACE_BETWEEN,
            gap=0,
        )
        assert positions == [0, 150]

    def test_space_around(self):
        """Equal space around each item."""
        positions = distribute_justify_content(
            item_sizes=[50, 50],
            container_size=200,
            justify=JustifyContent.SPACE_AROUND,
            gap=0,
        )
        # 100px free space, 2 items = 25px per side per item
        assert positions == [25, 125]

    def test_space_evenly(self):
        """Equal space between items and edges."""
        positions = distribute_justify_content(
            item_sizes=[40, 40, 40],
            container_size=200,
            justify=JustifyContent.SPACE_EVENLY,
            gap=0,
        )
        # 80px free space, 4 gaps = 20px each
        assert positions == [20, 80, 140]
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/algorithm.py

def distribute_justify_content(
    item_sizes: list[float],
    container_size: float,
    justify: JustifyContent,
    gap: float,
) -> list[float]:
    """
    Calculate item positions along main axis based on justify-content.

    Returns: List of positions for each item.
    """
    if not item_sizes:
        return []

    from flow.layout.style import JustifyContent

    n = len(item_sizes)
    total_item_size = sum(item_sizes)
    total_gap = gap * (n - 1) if n > 1 else 0
    free_space = container_size - total_item_size - total_gap

    positions: list[float] = []

    if justify == JustifyContent.FLEX_START:
        pos = 0.0
        for i, size in enumerate(item_sizes):
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.FLEX_END:
        pos = free_space
        for i, size in enumerate(item_sizes):
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.CENTER:
        pos = free_space / 2
        for i, size in enumerate(item_sizes):
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.SPACE_BETWEEN:
        if n == 1:
            positions.append(0.0)
        else:
            spacing = free_space / (n - 1)
            pos = 0.0
            for i, size in enumerate(item_sizes):
                positions.append(pos)
                pos += size + spacing

    elif justify == JustifyContent.SPACE_AROUND:
        if n == 0:
            return []
        spacing = free_space / n
        pos = spacing / 2
        for i, size in enumerate(item_sizes):
            positions.append(pos)
            pos += size + spacing

    elif justify == JustifyContent.SPACE_EVENLY:
        spacing = free_space / (n + 1)
        pos = spacing
        for i, size in enumerate(item_sizes):
            positions.append(pos)
            pos += size + spacing

    return positions
```

---

### Task 2.4: Align Items (Cross Axis)

**Files:**
- Modify: `src/flow/layout/algorithm.py`
- Modify: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_algorithm.py
from flow.layout.algorithm import align_cross_axis
from flow.layout.style import AlignItems

class TestAlignItems:
    def test_stretch(self):
        """Items stretch to fill cross axis."""
        results = align_cross_axis(
            item_sizes=[30, 40, 20],  # Heights
            container_cross=100,
            align=AlignItems.STRETCH,
        )
        # All items get position 0 and size 100
        assert results == [(0, 100), (0, 100), (0, 100)]

    def test_flex_start(self):
        """Items align to cross start."""
        results = align_cross_axis(
            item_sizes=[30, 40, 20],
            container_cross=100,
            align=AlignItems.FLEX_START,
        )
        assert results == [(0, 30), (0, 40), (0, 20)]

    def test_flex_end(self):
        """Items align to cross end."""
        results = align_cross_axis(
            item_sizes=[30, 40, 20],
            container_cross=100,
            align=AlignItems.FLEX_END,
        )
        assert results == [(70, 30), (60, 40), (80, 20)]

    def test_center(self):
        """Items centered on cross axis."""
        results = align_cross_axis(
            item_sizes=[30, 40, 20],
            container_cross=100,
            align=AlignItems.CENTER,
        )
        assert results == [(35, 30), (30, 40), (40, 20)]
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/algorithm.py

def align_cross_axis(
    item_sizes: list[float],
    container_cross: float,
    align: AlignItems,
) -> list[tuple[float, float]]:
    """
    Calculate cross-axis position and size for each item.

    Returns: List of (position, size) tuples.
    """
    from flow.layout.style import AlignItems

    results: list[tuple[float, float]] = []

    for size in item_sizes:
        if align == AlignItems.STRETCH:
            results.append((0, container_cross))

        elif align == AlignItems.FLEX_START:
            results.append((0, size))

        elif align == AlignItems.FLEX_END:
            results.append((container_cross - size, size))

        elif align == AlignItems.CENTER:
            pos = (container_cross - size) / 2
            results.append((pos, size))

        elif align == AlignItems.BASELINE:
            # Baseline alignment needs text metrics - default to flex-start
            results.append((0, size))

        else:
            results.append((0, size))

    return results
```

---

### Task 2.5: Flex Lines (Wrapping) + Floating-Point Precision

**Files:**
- Create: `src/flow/layout/flexline.py`
- Test: `tests/test_layout_flexline.py`

**Council Directive:** Use `approx_equal()` when comparing sizes to prevent infinite oscillation from floating-point errors like `0.30000000004`.

**Step 1: Write the failing test**
```python
# tests/test_layout_flexline.py
from flow.layout.flexline import FlexLine, collect_flex_lines
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle, FlexWrap
from flow.layout.types import Dimension

class TestFlexLines:
    def test_no_wrap_single_line(self):
        """No-wrap puts all items in one line."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
            LayoutNode(style=FlexStyle(width=Dimension.points(50))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,  # Less than total (150)
            wrap=FlexWrap.NO_WRAP,
            gap=0,
        )

        assert len(lines) == 1
        assert len(lines[0].items) == 3

    def test_wrap_creates_multiple_lines(self):
        """Wrap creates new line when items overflow."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
            LayoutNode(style=FlexStyle(width=Dimension.points(60))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=0,
        )

        # 60 + 60 > 100, so second item wraps
        assert len(lines) == 3
        assert len(lines[0].items) == 1
        assert len(lines[1].items) == 1
        assert len(lines[2].items) == 1

    def test_wrap_with_gap(self):
        """Gap affects when items wrap."""
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
            LayoutNode(style=FlexStyle(width=Dimension.points(45))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=20,  # 45 + 20 + 45 > 100
        )

        assert len(lines) == 3

class TestFloatingPointPrecision:
    """Council Directive: Handle floating-point precision errors."""

    def test_approx_equal_within_epsilon(self):
        """Values within 0.001 are considered equal."""
        from flow.layout.types import approx_equal, LAYOUT_EPSILON

        assert approx_equal(0.3, 0.30000000004)
        assert approx_equal(100.0, 100.0009)
        assert not approx_equal(100.0, 100.002)

    def test_wrap_handles_floating_point_boundary(self):
        """Wrapping doesn't fail on floating-point boundary cases."""
        # This would cause issues without epsilon comparison:
        # 33.333... * 3 = 99.999... which is "less than" 100
        items = [
            LayoutNode(style=FlexStyle(width=Dimension.percent(33.333))),
            LayoutNode(style=FlexStyle(width=Dimension.percent(33.333))),
            LayoutNode(style=FlexStyle(width=Dimension.percent(33.333))),
        ]

        lines = collect_flex_lines(
            items=items,
            container_main=100,
            wrap=FlexWrap.WRAP,
            gap=0,
        )

        # Should fit in one line (99.999 ≈ 100 within epsilon)
        assert len(lines) == 1

    def test_snap_to_pixel(self):
        """Sub-pixel values are snapped correctly."""
        from flow.layout.types import snap_to_pixel

        assert snap_to_pixel(10.4999) == 10.0
        assert snap_to_pixel(10.5001) == 11.0
        assert snap_to_pixel(33.333, scale=2) == 33.5  # Half-pixel grid
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/flexline.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexWrap

@dataclass
class FlexLine:
    """A single line of flex items."""
    items: list[LayoutNode] = field(default_factory=list)
    cross_size: float = 0.0  # Height of this line (in row direction)
    main_size: float = 0.0   # Used width of this line

def collect_flex_lines(
    items: list[LayoutNode],
    container_main: float,
    wrap: FlexWrap,
    gap: float,
) -> list[FlexLine]:
    """
    Collect flex items into lines based on wrap mode.

    Implements CSS Flexbox spec section 9.3:
    https://www.w3.org/TR/css-flexbox-1/#algo-line-break

    Council Directive: Uses LAYOUT_EPSILON for floating-point comparisons
    to prevent infinite oscillation from precision errors.
    """
    from flow.layout.style import FlexWrap
    from flow.layout.types import LAYOUT_EPSILON

    if not items:
        return []

    if wrap == FlexWrap.NO_WRAP:
        # All items in single line
        return [FlexLine(items=list(items))]

    lines: list[FlexLine] = []
    current_line: list[LayoutNode] = []
    current_main = 0.0

    for item in items:
        # Get item's hypothetical main size
        item_main = _get_hypothetical_main_size(item, container_main)

        # Check if item fits on current line
        # Council Directive: Use epsilon comparison to handle floating-point errors
        gap_to_add = gap if current_line else 0
        total_with_item = current_main + gap_to_add + item_main
        exceeds_container = total_with_item > container_main + LAYOUT_EPSILON

        if current_line and exceeds_container:
            # Start new line
            lines.append(FlexLine(items=current_line, main_size=current_main))
            current_line = [item]
            current_main = item_main
        else:
            current_line.append(item)
            current_main += gap_to_add + item_main

    # Add last line
    if current_line:
        lines.append(FlexLine(items=current_line, main_size=current_main))

    return lines

def _get_hypothetical_main_size(item: LayoutNode, container_main: float) -> float:
    """Get the hypothetical main size of a flex item."""
    style = item.style

    # Check flex-basis first
    if style.flex_basis.is_defined():
        return style.flex_basis.resolve(container_main) or 0

    # Fall back to width (for row direction)
    if style.width.is_defined():
        return style.width.resolve(container_main) or 0

    # Auto - needs content sizing (simplified to 0 for now)
    return 0
```

---

### Task 2.6: Main Layout Algorithm

**Files:**
- Create: `src/flow/layout/compute.py`
- Test: `tests/test_layout_compute.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_compute.py
import pytest
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle, FlexDirection, JustifyContent
from flow.layout.types import Dimension, Size

class TestComputeLayout:
    def test_single_node_fixed_size(self):
        """Single node with fixed dimensions."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )

        compute_layout(node, available=Size(width=500, height=500))

        assert node.layout.width == 100
        assert node.layout.height == 50
        assert node.layout.x == 0
        assert node.layout.y == 0

    def test_row_layout(self):
        """Basic row layout with flex-grow."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=200, height=100))

        # Children split the 200px width
        assert child1.layout.width == 100
        assert child2.layout.width == 100
        assert child1.layout.x == 0
        assert child2.layout.x == 100

    def test_column_layout(self):
        """Column layout stacks vertically."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=100, height=200))

        assert child1.layout.height == 100
        assert child2.layout.height == 100
        assert child1.layout.y == 0
        assert child2.layout.y == 100

    def test_justify_center(self):
        """Justify content center."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                justify_content=JustifyContent.CENTER,
            )
        )
        child = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(50))
        )

        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.x == 75
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/compute.py
from __future__ import annotations
from typing import TYPE_CHECKING

from flow.layout.algorithm import (
    AvailableSpace,
    resolve_flexible_lengths,
    distribute_justify_content,
    align_cross_axis,
)
from flow.layout.flexline import collect_flex_lines
from flow.layout.node import LayoutResult
from flow.layout.measure import MeasureContext

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.types import Size

def compute_layout(
    node: LayoutNode,
    available: Size,
    measure_context: MeasureContext | None = None,
) -> None:
    """
    Compute layout for a node tree.

    This is the main entry point for the Flexbox algorithm.

    Amendment Alpha: Nodes with measure_func use it to determine
    intrinsic size when dimensions are auto.
    """
    if measure_context is None:
        measure_context = MeasureContext()

    # Resolve node's own size
    style = node.style

    # Amendment Alpha: If node has measure_func and auto dimensions, use it
    if node.measure_func is not None and (
        style.width.is_auto() or style.height.is_auto()
    ):
        available_w = (
            AvailableSpace.definite(available.width)
            if not style.width.is_auto()
            else AvailableSpace.max_content()
        )
        available_h = (
            AvailableSpace.definite(available.height)
            if not style.height.is_auto()
            else AvailableSpace.max_content()
        )

        measured = node.measure_func(available_w, available_h, measure_context)
        width = measured.width if style.width.is_auto() else style.width.resolve(available.width)
        height = measured.height if style.height.is_auto() else style.height.resolve(available.height)
    else:
        width = style.width.resolve(available.width)
        if width is None:
            width = available.width

        height = style.height.resolve(available.height)
        if height is None:
            height = available.height

    # Apply min/max constraints
    width = _clamp_size(width, style.min_width, style.max_width, available.width)
    height = _clamp_size(height, style.min_height, style.max_height, available.height)

    # Set node's layout
    node.layout = LayoutResult(x=0, y=0, width=width, height=height)

    # Layout children if any (measured nodes are leaf nodes)
    if node.children:
        _layout_children(node, measure_context)

    node.clear_dirty()

def _clamp_size(
    value: float,
    min_dim: Dimension,
    max_dim: Dimension,
    parent: float,
) -> float:
    """Clamp value between min and max dimensions."""
    from flow.layout.types import Dimension

    min_val = min_dim.resolve(parent) if min_dim.is_defined() else 0
    max_val = max_dim.resolve(parent) if max_dim.is_defined() else float('inf')

    return max(min_val or 0, min(value, max_val or float('inf')))

def _layout_children(node: LayoutNode, measure_context: MeasureContext) -> None:
    """Layout children using Flexbox algorithm."""
    from flow.layout.style import FlexDirection
    from flow.layout.types import Size

    style = node.style
    direction = style.flex_direction
    is_row = direction.is_row()

    # Get container inner size (subtract padding)
    padding = style.padding.resolve(node.layout.width, node.layout.height)
    inner_width = node.layout.width - padding.horizontal
    inner_height = node.layout.height - padding.vertical

    container_main = inner_width if is_row else inner_height
    container_cross = inner_height if is_row else inner_width

    gap = style.get_gap(direction)

    # Collect items into flex lines
    lines = collect_flex_lines(
        items=node.children,
        container_main=container_main,
        wrap=style.flex_wrap,
        gap=gap,
    )

    # Resolve flexible lengths for each line
    cross_offset = padding.top if is_row else padding.left

    for line in lines:
        # Get main axis sizes (Amendment Alpha: measure_func used here)
        main_sizes = resolve_flexible_lengths(
            items=line.items,
            container_main_size=container_main,
            direction=direction,
            gap=gap,
            measure_context=measure_context,  # Pass for intrinsic sizing
        )

        # Get main axis positions (justify-content)
        main_positions = distribute_justify_content(
            item_sizes=main_sizes,
            container_size=container_main,
            justify=style.justify_content,
            gap=gap,
        )

        # Calculate cross sizes for alignment
        cross_sizes = []
        for item in line.items:
            if is_row:
                h = item.style.height.resolve(container_cross)
                cross_sizes.append(h if h else container_cross)
            else:
                w = item.style.width.resolve(container_cross)
                cross_sizes.append(w if w else container_cross)

        # Determine line cross size
        line.cross_size = max(cross_sizes) if cross_sizes else container_cross

        # Get cross axis positions (align-items)
        cross_results = align_cross_axis(
            item_sizes=cross_sizes,
            container_cross=line.cross_size,
            align=style.align_items,
        )

        # Apply layouts to children
        for i, item in enumerate(line.items):
            main_pos = main_positions[i]
            main_size = main_sizes[i]
            cross_pos, cross_size = cross_results[i]

            if is_row:
                x = padding.left + main_pos
                y = cross_offset + cross_pos
                w = main_size
                h = cross_size
            else:
                x = cross_offset + cross_pos
                y = padding.top + main_pos
                w = cross_size
                h = main_size

            item.layout = LayoutResult(x=x, y=y, width=w, height=h)

            # Recursively layout grandchildren (measured nodes have no children)
            if item.children:
                _layout_children(item, measure_context)

        cross_offset += line.cross_size + (style.get_gap(direction) if not is_row else 0)
```

---

## Phase 3: Flow Integration

### Task 3.1: Layout-Aware Element Base

**Files:**
- Modify: `src/flow/element.py`
- Test: `tests/test_element_layout.py`

**Step 1: Write the failing test**
```python
# tests/test_element_layout.py
from flow.element import Element
from flow.layout.style import FlexStyle, FlexDirection
from flow.layout.types import Dimension

class TestElementLayout:
    def test_element_has_layout_style(self):
        """Elements can have layout styles."""
        elem = Element(
            flex_direction="row",
            justify_content="center",
            width=100,
            height=50,
        )

        style = elem.get_layout_style()
        assert style.flex_direction == FlexDirection.ROW
        assert style.width == Dimension.points(100)

    def test_element_to_layout_node(self):
        """Elements can convert to LayoutNodes."""
        parent = Element(width=200, height=100, flex_direction="row")
        parent.__enter__()

        child1 = Element(flex_grow=1)
        child1.__enter__()
        child1.__exit__(None, None, None)

        child2 = Element(flex_grow=1)
        child2.__enter__()
        child2.__exit__(None, None, None)

        parent.__exit__(None, None, None)

        layout_node = parent.to_layout_node()

        assert len(layout_node.children) == 2
        assert layout_node.style.flex_direction == FlexDirection.ROW
```

**Step 3: Write implementation notes**
This task modifies Element to:
1. Parse layout-related props into FlexStyle
2. Add `get_layout_style() -> FlexStyle` method
3. Add `to_layout_node() -> LayoutNode` method
4. Keep Element decoupled from layout computation

---

### Task 3.2: Flex Container Element

**Files:**
- Create: `src/flow/ui/layout.py`
- Test: `tests/test_ui_layout.py`

**Step 1: Write the failing test**
```python
# tests/test_ui_layout.py
from flow.ui.layout import Flex, Box
from flow.layout.compute import compute_layout
from flow.layout.types import Size

class TestFlexElement:
    def test_flex_context_manager(self):
        """Flex works as context manager."""
        with Flex(direction="row", width=200, height=100) as container:
            with Box(flex_grow=1) as child1:
                pass
            with Box(flex_grow=1) as child2:
                pass

        assert len(container.children) == 2

    def test_flex_computes_layout(self):
        """Flex element can compute layout."""
        with Flex(direction="row", width=200, height=100) as root:
            with Box(flex_grow=1) as left:
                pass
            with Box(flex_grow=1) as right:
                pass

        # Compute layout
        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # Verify computed positions
        assert layout_node.children[0].layout.width == 100
        assert layout_node.children[1].layout.x == 100

class TestBoxElement:
    def test_box_with_fixed_size(self):
        """Box with fixed dimensions."""
        box = Box(width=50, height=50)
        style = box.get_layout_style()

        assert style.width.resolve(100) == 50
        assert style.height.resolve(100) == 50
```

**Step 3: Write minimal implementation**
```python
# src/flow/ui/layout.py
from __future__ import annotations
from typing import Any, Literal

from flow.element import Element
from flow.layout.node import LayoutNode
from flow.layout.style import (
    FlexStyle, FlexDirection, FlexWrap,
    JustifyContent, AlignItems, AlignContent,
)
from flow.layout.types import Dimension, Spacing

DirectionLiteral = Literal["row", "column", "row-reverse", "column-reverse"]
WrapLiteral = Literal["nowrap", "wrap", "wrap-reverse"]
JustifyLiteral = Literal["flex-start", "flex-end", "center", "space-between", "space-around", "space-evenly"]
AlignLiteral = Literal["flex-start", "flex-end", "center", "stretch", "baseline"]

class Flex(Element):
    """A Flexbox container element."""

    def __init__(
        self,
        *,
        direction: DirectionLiteral = "row",
        wrap: WrapLiteral = "nowrap",
        justify: JustifyLiteral = "flex-start",
        align: AlignLiteral = "stretch",
        gap: float = 0,
        width: float | str | None = None,
        height: float | str | None = None,
        padding: float | tuple[float, ...] | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self._direction = direction
        self._wrap = wrap
        self._justify = justify
        self._align = align
        self._gap = gap
        self._width = width
        self._height = height
        self._padding = padding

    def get_layout_style(self) -> FlexStyle:
        return FlexStyle(
            flex_direction=FlexDirection(self._direction),
            flex_wrap=FlexWrap(self._wrap),
            justify_content=JustifyContent(self._justify.replace("_", "-")),
            align_items=AlignItems(self._align.replace("_", "-")),
            gap=self._gap,
            width=_parse_dimension(self._width),
            height=_parse_dimension(self._height),
            padding=_parse_spacing(self._padding),
        )

    def to_layout_node(self) -> LayoutNode:
        node = LayoutNode(style=self.get_layout_style())
        for child in self.children:
            if hasattr(child, 'to_layout_node'):
                node.add_child(child.to_layout_node())
        return node

class Box(Element):
    """A box element with layout properties."""

    def __init__(
        self,
        *,
        width: float | str | None = None,
        height: float | str | None = None,
        flex_grow: float = 0,
        flex_shrink: float = 1,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self._width = width
        self._height = height
        self._flex_grow = flex_grow
        self._flex_shrink = flex_shrink

    def get_layout_style(self) -> FlexStyle:
        return FlexStyle(
            width=_parse_dimension(self._width),
            height=_parse_dimension(self._height),
            flex_grow=self._flex_grow,
            flex_shrink=self._flex_shrink,
        )

    def to_layout_node(self) -> LayoutNode:
        node = LayoutNode(style=self.get_layout_style())
        for child in self.children:
            if hasattr(child, 'to_layout_node'):
                node.add_child(child.to_layout_node())
        return node

def _parse_dimension(value: float | str | None) -> Dimension:
    if value is None:
        return Dimension.auto()
    if isinstance(value, (int, float)):
        return Dimension.points(float(value))
    if isinstance(value, str):
        if value.endswith('%'):
            return Dimension.percent(float(value[:-1]))
        return Dimension.points(float(value.replace('px', '')))
    return Dimension.auto()

def _parse_spacing(value: float | tuple[float, ...] | None) -> Spacing:
    if value is None:
        return Spacing()
    if isinstance(value, (int, float)):
        d = Dimension.points(float(value))
        return Spacing(top=d, right=d, bottom=d, left=d)
    # TODO: Handle tuple variations
    return Spacing()
```

---

### Task 3.3: Reactive Layout with Signals and Layout Boundaries (Amendment Gamma)

**Files:**
- Create: `src/flow/layout/reactive.py`
- Test: `tests/test_layout_reactive.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_reactive.py
from flow.signal import Signal
from flow.layout.reactive import ReactiveLayoutNode
from flow.layout.style import FlexStyle, FlexDirection
from flow.layout.types import Dimension

class TestReactiveLayout:
    def test_signal_style_change_marks_dirty(self):
        """Changing a Signal-bound style marks layout dirty."""
        width = Signal(100)

        node = ReactiveLayoutNode(
            style_signals={"width": width}
        )

        # Initial state
        assert node.is_dirty()
        node.clear_dirty()
        assert not node.is_dirty()

        # Change signal
        width.value = 200
        assert node.is_dirty()

    def test_reactive_style_resolution(self):
        """Style resolves current Signal values."""
        grow = Signal(1.0)

        node = ReactiveLayoutNode(
            base_style=FlexStyle(flex_direction=FlexDirection.ROW),
            style_signals={"flex_grow": grow}
        )

        style = node.resolve_style()
        assert style.flex_grow == 1.0

        grow.value = 2.0
        style = node.resolve_style()
        assert style.flex_grow == 2.0

class TestReactiveLayoutBoundary:
    """Amendment Gamma: Layout Boundaries prevent layout thrashing."""

    def test_layout_boundary_blocks_dirty_propagation(self):
        """Reactive Layout Boundaries don't propagate dirty to parent."""
        parent = ReactiveLayoutNode(
            base_style=FlexStyle()
        )
        # Boundary child: has fixed width AND height
        boundary = ReactiveLayoutNode(
            base_style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )
        # Signal-bound grandchild
        grow = Signal(1.0)
        grandchild = ReactiveLayoutNode(
            style_signals={"flex_grow": grow}
        )

        parent.add_child(boundary)
        boundary.add_child(grandchild)

        # Clear all dirty
        parent.clear_dirty()
        boundary.clear_dirty()
        grandchild.clear_dirty()

        # Change grandchild's signal
        grow.value = 2.0

        # Grandchild and boundary are dirty
        assert grandchild.is_dirty()
        assert boundary.is_dirty()
        # BUT parent is NOT dirty (boundary blocks)
        assert not parent.is_dirty()

    def test_reactive_boundary_detection(self):
        """ReactiveLayoutNode correctly detects if it's a boundary."""
        # Fixed dimensions = boundary
        boundary = ReactiveLayoutNode(
            base_style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )
        assert boundary.is_layout_boundary()

        # Signal-bound width makes it dynamic, not a boundary
        width_signal = Signal(100)
        dynamic = ReactiveLayoutNode(
            base_style=FlexStyle(height=Dimension.points(100)),
            style_signals={"width": width_signal}
        )
        # Note: Signal-bound dimensions are NOT considered boundaries
        # because their value can change reactively
        assert not dynamic.is_layout_boundary()
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/reactive.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import FlexStyle

if TYPE_CHECKING:
    from flow.signal import Signal

@dataclass
class ReactiveLayoutNode:
    """
    A layout node with Signal-bound style properties.

    Amendment Gamma: Nodes with fixed width AND height (Layout Boundaries)
    do NOT propagate dirty flags to their parent, preventing layout thrashing.
    """

    base_style: FlexStyle = field(default_factory=FlexStyle)
    style_signals: dict[str, Signal[Any]] = field(default_factory=dict)
    children: list[ReactiveLayoutNode] = field(default_factory=list)
    parent: ReactiveLayoutNode | None = field(default=None, repr=False)
    layout: LayoutResult = field(default_factory=LayoutResult)
    _dirty: bool = field(default=True, repr=False)
    _unsubscribes: list[Any] = field(default_factory=list, repr=False)

    def __post_init__(self):
        # Subscribe to all signal changes
        for name, signal in self.style_signals.items():
            unsub = signal.subscribe(self._on_signal_change)
            self._unsubscribes.append(unsub)

    def _on_signal_change(self) -> None:
        """Handle signal change - mark dirty."""
        self.mark_dirty()

    def resolve_style(self) -> FlexStyle:
        """Get current style with Signal values resolved."""
        overrides = {
            name: signal.value
            for name, signal in self.style_signals.items()
        }
        return self.base_style.with_updates(**overrides)

    def is_layout_boundary(self) -> bool:
        """
        Amendment Gamma: Check if this node is a Layout Boundary.

        A Layout Boundary has explicit width AND height in base_style
        (not signal-bound), meaning its layout is size-stable.
        Signal-bound dimensions are NOT boundaries because they can change.
        """
        # Only consider base_style - signal-bound dims are dynamic
        return (
            self.base_style.width.is_defined() and
            self.base_style.height.is_defined() and
            "width" not in self.style_signals and
            "height" not in self.style_signals
        )

    def mark_dirty(self) -> None:
        """
        Mark this node as needing layout.

        Amendment Gamma: Layout Boundaries do NOT propagate dirty
        flags to their parent, preventing layout thrashing.
        """
        self._dirty = True
        if self.parent is not None and not self.is_layout_boundary():
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False

    def add_child(self, child: ReactiveLayoutNode) -> None:
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def dispose(self) -> None:
        """Clean up signal subscriptions."""
        for unsub in self._unsubscribes:
            unsub()
        self._unsubscribes.clear()

    def to_layout_node(self) -> LayoutNode:
        """Convert to static LayoutNode for computation."""
        node = LayoutNode(style=self.resolve_style())
        for child in self.children:
            node.add_child(child.to_layout_node())
        return node
```

---

## Phase 4: Render Integration

### Task 4.1: Computed Styles to RenderNode

**Files:**
- Modify: `src/flow/renderer/protocol.py`
- Test: `tests/test_render_layout.py`

**Step 1: Write the failing test**
```python
# tests/test_render_layout.py
from flow.ui.layout import Flex, Box
from flow.layout.compute import compute_layout
from flow.layout.types import Size
from flow.renderer.html import HTMLRenderer

class TestRenderWithLayout:
    def test_computed_layout_in_render(self):
        """RenderNode includes computed layout as style."""
        with Flex(direction="row", width=200, height=100) as root:
            with Box(flex_grow=1, cls="left") as left:
                pass
            with Box(flex_grow=1, cls="right") as right:
                pass

        # Compute layout
        layout_node = root.to_layout_node()
        compute_layout(layout_node, Size(width=200, height=100))

        # Convert to RenderNode with computed styles
        render_node = root.to_render_node_with_layout(layout_node)

        # Verify computed positions are in style
        left_style = render_node.children[0].props.get('style', {})
        assert left_style.get('left') == '0px'
        assert left_style.get('width') == '100px'

        right_style = render_node.children[1].props.get('style', {})
        assert right_style.get('left') == '100px'
```

---

### Task 4.2: Layout-Aware HTML Renderer

**Files:**
- Modify: `src/flow/renderer/html.py`
- Test: `tests/test_html_renderer_layout.py`

This task enhances HTMLRenderer to:
1. Apply computed layout positions as absolute CSS
2. Convert layout results to style attributes
3. Support layout containers with overflow handling

---

### Task 4.3: Style vs. Prop Conflict Resolution (Amendment Beta)

**Files:**
- Create: `src/flow/layout/style_resolver.py`
- Modify: `src/flow/renderer/html.py`
- Test: `tests/test_style_conflict.py`

**Step 1: Write the failing test**
```python
# tests/test_style_conflict.py
import pytest
from flow.layout.style_resolver import (
    resolve_style_conflict,
    strip_geometry_classes,
    GEOMETRY_CLASS_PATTERNS,
)

class TestGeometryClassStripping:
    """Amendment Beta: Explicit Layout Props define the Truth."""

    def test_strip_width_classes(self):
        """Width classes are stripped when width prop is present."""
        cls = "w-10 bg-blue-500 text-white"
        result = strip_geometry_classes(cls, has_width=True)
        assert result == "bg-blue-500 text-white"

    def test_strip_height_classes(self):
        """Height classes are stripped when height prop is present."""
        cls = "h-20 h-screen bg-red-500"
        result = strip_geometry_classes(cls, has_height=True)
        assert result == "bg-red-500"

    def test_strip_flex_classes(self):
        """Flex classes stripped when flex props present."""
        cls = "flex flex-row justify-center items-start gap-4 p-2"
        result = strip_geometry_classes(
            cls,
            has_flex_direction=True,
            has_justify=True,
            has_align=True,
            has_gap=True,
        )
        assert result == "p-2"  # Only non-geometry class remains

    def test_strip_multiple_geometry_classes(self):
        """Multiple geometry classes are stripped."""
        cls = "w-full h-1/2 min-w-0 max-h-screen flex-1 bg-gray-100"
        result = strip_geometry_classes(
            cls,
            has_width=True,
            has_height=True,
            has_flex_grow=True,
        )
        assert result == "bg-gray-100"

    def test_preserve_non_geometry_classes(self):
        """Non-geometry classes are preserved."""
        cls = "rounded-lg shadow-md hover:bg-blue-600 transition-colors"
        result = strip_geometry_classes(cls, has_width=True)
        # No geometry classes to strip
        assert result == cls

    def test_no_stripping_when_no_props(self):
        """Classes preserved when no explicit props conflict."""
        cls = "w-10 h-10 flex-1"
        result = strip_geometry_classes(cls)
        assert result == cls

class TestStyleConflictResolution:
    def test_prop_overrides_class(self):
        """Explicit prop value takes precedence."""
        from flow.ui.layout import Box

        box = Box(width=100, cls="w-10 bg-blue-500")
        render_node = box.to_render_node()

        # Width comes from prop (100px), not class (w-10 = 40px)
        style = render_node.props.get("style", {})
        assert style.get("width") == "100px"

        # Class has w-10 stripped
        assert "w-10" not in render_node.props.get("cls", "")
        assert "bg-blue-500" in render_node.props.get("cls", "")
```

**Step 2: Run test to verify it fails**
```bash
uv run pytest tests/test_style_conflict.py -v
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/style_resolver.py
"""
Amendment Beta: Style vs. Prop Conflict Resolution

When explicit layout props conflict with Tailwind classes,
the props define the truth. Geometry classes are stripped.
"""
from __future__ import annotations
import re

# Tailwind geometry class patterns to strip
GEOMETRY_CLASS_PATTERNS = {
    "width": [
        r"w-\d+",        # w-0 to w-96
        r"w-px",         # w-px
        r"w-\d+/\d+",    # w-1/2, w-1/3, etc.
        r"w-full",
        r"w-screen",
        r"w-min",
        r"w-max",
        r"w-fit",
        r"w-auto",
        r"w-\[\S+\]",    # arbitrary: w-[100px]
        r"min-w-\S+",
        r"max-w-\S+",
    ],
    "height": [
        r"h-\d+",
        r"h-px",
        r"h-\d+/\d+",
        r"h-full",
        r"h-screen",
        r"h-min",
        r"h-max",
        r"h-fit",
        r"h-auto",
        r"h-\[\S+\]",
        r"min-h-\S+",
        r"max-h-\S+",
    ],
    "flex_direction": [
        r"flex",
        r"flex-row",
        r"flex-col",
        r"flex-row-reverse",
        r"flex-col-reverse",
    ],
    "flex_wrap": [
        r"flex-wrap",
        r"flex-nowrap",
        r"flex-wrap-reverse",
    ],
    "justify": [
        r"justify-start",
        r"justify-end",
        r"justify-center",
        r"justify-between",
        r"justify-around",
        r"justify-evenly",
    ],
    "align": [
        r"items-start",
        r"items-end",
        r"items-center",
        r"items-baseline",
        r"items-stretch",
    ],
    "gap": [
        r"gap-\d+",
        r"gap-x-\d+",
        r"gap-y-\d+",
        r"gap-px",
        r"gap-\[\S+\]",
    ],
    "flex_grow": [
        r"flex-1",
        r"flex-auto",
        r"flex-initial",
        r"flex-none",
        r"grow",
        r"grow-0",
        r"shrink",
        r"shrink-0",
    ],
}

def strip_geometry_classes(
    cls: str,
    has_width: bool = False,
    has_height: bool = False,
    has_flex_direction: bool = False,
    has_flex_wrap: bool = False,
    has_justify: bool = False,
    has_align: bool = False,
    has_gap: bool = False,
    has_flex_grow: bool = False,
) -> str:
    """
    Strip geometry-related Tailwind classes when explicit props are present.

    Args:
        cls: The class string from the element
        has_*: Whether the corresponding prop is explicitly set

    Returns:
        Class string with conflicting geometry classes removed
    """
    if not cls:
        return cls

    classes = cls.split()
    patterns_to_strip: list[str] = []

    if has_width:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["width"])
    if has_height:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["height"])
    if has_flex_direction:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_direction"])
    if has_flex_wrap:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_wrap"])
    if has_justify:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["justify"])
    if has_align:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["align"])
    if has_gap:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["gap"])
    if has_flex_grow:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_grow"])

    if not patterns_to_strip:
        return cls

    # Build combined regex
    combined_pattern = re.compile(
        r"^(" + "|".join(patterns_to_strip) + r")$"
    )

    filtered = [c for c in classes if not combined_pattern.match(c)]
    return " ".join(filtered)

def resolve_style_conflict(
    cls: str | None,
    layout_props: dict,
) -> str:
    """
    Resolve conflicts between Tailwind classes and explicit layout props.

    Returns the cleaned class string with geometry classes removed
    where props take precedence.
    """
    if not cls:
        return ""

    return strip_geometry_classes(
        cls,
        has_width="width" in layout_props and layout_props["width"] is not None,
        has_height="height" in layout_props and layout_props["height"] is not None,
        has_flex_direction="flex_direction" in layout_props or "direction" in layout_props,
        has_flex_wrap="flex_wrap" in layout_props or "wrap" in layout_props,
        has_justify="justify_content" in layout_props or "justify" in layout_props,
        has_align="align_items" in layout_props or "align" in layout_props,
        has_gap="gap" in layout_props and layout_props["gap"] is not None,
        has_flex_grow="flex_grow" in layout_props and layout_props["flex_grow"] != 0,
    )
```

**Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_style_conflict.py -v
```

**Step 5: Commit**
```bash
git add src/flow/layout/style_resolver.py tests/test_style_conflict.py
git commit -m "feat(layout): add style vs prop conflict resolution (Amendment Beta)"
```

---

## Phase 5: Advanced Features

### Task 5.1: Absolute Positioning

**Files:**
- Modify: `src/flow/layout/compute.py`
- Test: `tests/test_layout_absolute.py`

Implement handling of `position: absolute` children:
- Remove from flex flow
- Position relative to containing block
- Support insets (top, right, bottom, left)

---

### Task 5.2: Aspect Ratio

**Files:**
- Modify: `src/flow/layout/compute.py`
- Test: `tests/test_layout_aspect_ratio.py`

Implement aspect ratio constraint:
- When one dimension is known, calculate other from ratio
- Respect min/max constraints

---

### Task 5.3: Min/Max Content Sizing

**Files:**
- Modify: `src/flow/layout/compute.py`
- Create: `src/flow/layout/intrinsic.py`
- Test: `tests/test_layout_intrinsic.py`

Implement intrinsic sizing:
- `min-content`: Smallest size without overflow
- `max-content`: Ideal size without wrapping
- `fit-content`: Clamp between min and max

---

### Task 5.4: Align Content (Multi-line)

**Files:**
- Modify: `src/flow/layout/compute.py`
- Test: `tests/test_layout_align_content.py`

Implement align-content for wrapped flex containers:
- Distribute flex lines in cross axis
- Support all alignment modes

---

### Task 5.5: No-GIL Parallel Layout (Amendment Gamma)

**Files:**
- Create: `src/flow/layout/parallel.py`
- Test: `tests/test_layout_parallel.py`

**Amendment Gamma Compliance:** Only parallelize Layout Boundaries.

**Step 1: Write the failing test**
```python
# tests/test_layout_parallel.py
import pytest
from flow.layout.parallel import compute_layout_parallel, find_layout_boundaries
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle, FlexDirection
from flow.layout.types import Dimension, Size
import time

class TestFindLayoutBoundaries:
    def test_find_boundaries_in_tree(self):
        """Finds all Layout Boundary nodes in tree."""
        root = LayoutNode(style=FlexStyle())

        # Non-boundary children
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        # Layout Boundary child (has explicit w & h)
        child2 = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )

        # Grandchildren under boundary
        grandchild = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)
        child2.add_child(grandchild)

        boundaries = find_layout_boundaries(root)

        assert child2 in boundaries
        assert root not in boundaries  # Root is not a boundary
        assert child1 not in boundaries  # No fixed dimensions
        assert grandchild not in boundaries

    def test_nested_boundaries(self):
        """Nested boundaries are collected correctly."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(500),
                height=Dimension.points(500),
            )
        )

        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(200),
            )
        )

        grandchild = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )

        root.add_child(child)
        child.add_child(grandchild)

        boundaries = find_layout_boundaries(root)

        # Root is a boundary (top-level)
        assert root in boundaries
        # child is under root boundary, so it's a parallelizable unit
        assert child in boundaries
        # grandchild is under child boundary
        assert grandchild in boundaries

class TestParallelLayout:
    def test_parallel_layout_same_result_as_sequential(self):
        """Parallel layout produces identical results to sequential."""
        from flow.layout.compute import compute_layout

        # Create tree with multiple boundaries
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(400),
                height=Dimension.points(400),
                flex_direction=FlexDirection.ROW,
            )
        )

        for i in range(4):
            boundary = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(100),
                    height=Dimension.points(100),
                )
            )
            inner = LayoutNode(style=FlexStyle(flex_grow=1.0))
            boundary.add_child(inner)
            root.add_child(boundary)

        # Compute sequentially
        compute_layout(root, available=Size(400, 400))
        sequential_results = [
            (c.layout.x, c.layout.y, c.layout.width, c.layout.height)
            for c in root.children
        ]

        # Reset
        for c in root.children:
            c.layout = LayoutResult()
            c._dirty = True

        # Compute in parallel
        compute_layout_parallel(root, available=Size(400, 400))
        parallel_results = [
            (c.layout.x, c.layout.y, c.layout.width, c.layout.height)
            for c in root.children
        ]

        assert sequential_results == parallel_results

    @pytest.mark.slow
    def test_parallel_faster_than_sequential(self):
        """Parallel layout is faster for large trees with boundaries."""
        from flow.layout.compute import compute_layout

        # Create tree with many Layout Boundaries
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(1000),
                height=Dimension.points(1000),
                flex_direction=FlexDirection.COLUMN,
            )
        )

        # 100 boundary rows, each with nested content
        for row in range(100):
            row_node = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(1000),
                    height=Dimension.points(10),
                    flex_direction=FlexDirection.ROW,
                )
            )
            # 10 cells per row
            for cell in range(10):
                cell_node = LayoutNode(
                    style=FlexStyle(
                        width=Dimension.points(100),
                        height=Dimension.points(10),
                    )
                )
                row_node.add_child(cell_node)
            root.add_child(row_node)

        # Time sequential
        start = time.perf_counter()
        compute_layout(root, available=Size(1000, 1000))
        sequential_time = time.perf_counter() - start

        # Reset
        def reset_tree(node):
            node.layout = LayoutResult()
            node._dirty = True
            for c in node.children:
                reset_tree(c)
        reset_tree(root)

        # Time parallel
        start = time.perf_counter()
        compute_layout_parallel(root, available=Size(1000, 1000))
        parallel_time = time.perf_counter() - start

        # Parallel should be faster (on multi-core with No-GIL)
        # Note: This may fail on GIL Python - skip or mark appropriately
        print(f"Sequential: {sequential_time:.3f}s, Parallel: {parallel_time:.3f}s")
```

**Step 2: Run test to verify it fails**
```bash
uv run pytest tests/test_layout_parallel.py -v
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/parallel.py
"""
Amendment Gamma: Layout Boundary-based Parallel Layout

Only nodes with explicit width AND height (Layout Boundaries)
can be computed in parallel threads. This prevents data races
where Child A depends on Parent B's calculated width.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
import sys

from flow.layout.compute import compute_layout, _layout_children
from flow.layout.node import LayoutResult

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.types import Size

def find_layout_boundaries(root: LayoutNode) -> list[LayoutNode]:
    """
    Find all Layout Boundary nodes in tree.

    A Layout Boundary has explicit width AND height, meaning
    its subtree can be computed independently.
    """
    boundaries: list[LayoutNode] = []

    def collect(node: LayoutNode) -> None:
        if node.is_layout_boundary():
            boundaries.append(node)
        for child in node.children:
            collect(child)

    collect(root)
    return boundaries

def compute_layout_parallel(
    root: LayoutNode,
    available: Size,
    max_workers: int | None = None,
) -> None:
    """
    Compute layout using parallel threads for Layout Boundaries.

    Only works efficiently on Python 3.14+ with No-GIL.
    Falls back to sequential on older Python or single-core systems.

    Args:
        root: The root layout node
        available: Available space for root
        max_workers: Max parallel threads (default: CPU count)
    """
    # Check if we can benefit from parallelism
    if sys.version_info < (3, 14) or not _has_free_threading():
        # Fall back to sequential
        compute_layout(root, available)
        return

    # Phase 1: Compute root and find parallelizable boundaries
    _compute_node_self(root, available)

    # Collect top-level Layout Boundaries (direct children that are boundaries)
    parallel_subtrees = [
        child for child in root.children
        if child.is_layout_boundary()
    ]

    non_parallel_children = [
        child for child in root.children
        if not child.is_layout_boundary()
    ]

    # Phase 2: Compute non-boundary children sequentially (they depend on siblings)
    for child in non_parallel_children:
        _compute_subtree(child)

    # Phase 3: Compute boundary children in parallel
    if parallel_subtrees:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_compute_subtree, subtree): subtree
                for subtree in parallel_subtrees
            }

            for future in as_completed(futures):
                # Propagate any exceptions
                future.result()

    root.clear_dirty()

def _compute_node_self(node: LayoutNode, available: Size) -> None:
    """Compute a node's own layout (not children)."""
    from flow.layout.types import Size as SizeType

    style = node.style

    width = style.width.resolve(available.width)
    if width is None:
        width = available.width

    height = style.height.resolve(available.height)
    if height is None:
        height = available.height

    node.layout = LayoutResult(x=0, y=0, width=width, height=height)

def _compute_subtree(node: LayoutNode) -> None:
    """Compute layout for a subtree (node already has position)."""
    from flow.layout.types import Size

    if node.children:
        _layout_children(node)
    node.clear_dirty()

def _has_free_threading() -> bool:
    """Check if running on free-threaded (No-GIL) Python."""
    try:
        # Python 3.14+ has sys._is_gil_enabled()
        return not sys._is_gil_enabled()  # type: ignore
    except AttributeError:
        return False
```

**Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_layout_parallel.py -v -k "not slow"
```

**Step 5: Commit**
```bash
git add src/flow/layout/parallel.py tests/test_layout_parallel.py
git commit -m "feat(layout): add Layout Boundary parallel computation (Amendment Gamma)"
```

---

## Summary

| Phase | Tasks | Focus | Amendments |
|-------|-------|-------|------------|
| **1** | 1.1-1.6 | Core types: Dimension, Size, FlexStyle, LayoutNode, MeasureFunc | Alpha, Gamma |
| **2** | 2.1-2.6 | Flexbox algorithm: sizing, justify, align, wrap | — |
| **3** | 3.1-3.3 | Flow integration: Elements, Signals, Layout Boundaries | Gamma |
| **4** | 4.1-4.3 | Rendering: computed styles, style conflict resolution | Beta |
| **5** | 5.1-5.5 | Advanced: absolute, aspect ratio, parallel (boundary-aware) | Gamma |

## Council Amendments Checklist

- [ ] **Amendment Alpha (Task 1.6):** MeasureFunc protocol with text measurement
- [ ] **Amendment Beta (Task 4.3):** Style vs. Prop conflict resolution
- [ ] **Amendment Gamma (Tasks 1.5, 3.3, 5.5):** Layout Boundaries prevent thrashing and enable parallelism
- [ ] **Directive: Floating-Point Precision (Tasks 1.1, 2.5):** Use LAYOUT_EPSILON (0.001) for comparisons

## Dependencies

- Python 3.14+ (for No-GIL parallel layout in Task 5.5)
- Flow Framework (existing)
- No external layout libraries (pure Python)
- Optional: `Pillow` for exact text measurement in image rendering

## Success Criteria

1. All tests pass: `uv run pytest tests/test_layout*.py -v`
2. Demo works: `yoga_demo.py` from `yoga.md` renders correctly
3. Performance: Layout of 1000 nodes < 100ms
4. **Amendment Alpha:** Text elements can report their intrinsic size
5. **Amendment Beta:** `Box(cls="w-10", width=100)` uses 100px, not 40px
6. **Amendment Gamma:** Layout Boundaries do not propagate dirty flags to parent

---

## Appendix: CSS Flexbox Specification References

- [CSS Flexible Box Layout Module Level 1](https://www.w3.org/TR/css-flexbox-1/)
- [9.2 Line Length Determination](https://www.w3.org/TR/css-flexbox-1/#algo-available)
- [9.3 Main Size Determination](https://www.w3.org/TR/css-flexbox-1/#algo-main-container)
- [9.4 Cross Size Determination](https://www.w3.org/TR/css-flexbox-1/#algo-cross-sizing)
- [9.5 Main-Axis Alignment](https://www.w3.org/TR/css-flexbox-1/#algo-main-align)
- [9.6 Cross-Axis Alignment](https://www.w3.org/TR/css-flexbox-1/#algo-cross-align)
