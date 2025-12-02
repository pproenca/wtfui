# Yoga Layout Engine for Flow - Implementation Plan

> **Goal:** Implement a pure Python Flexbox layout engine integrated with Flow's reactive system
> **Tech Stack:** Python 3.14+, Flow Framework, No external dependencies
> **Skills Reference:** See @.cursor/skills/test-driven-development.md for TDD protocol

---

## Overview

This plan implements a **Python Flexbox layout engine** inspired by Meta's [Yoga](https://www.yogalayout.dev/) and Dioxus's [Taffy](https://docs.rs/taffy/). The engine computes layout positions for Flow UI elements following the [CSS Flexbox specification](https://www.w3.org/TR/css-flexbox-1/).

### Design Principles (from MANIFEST.md)

1. **Indentation is Topology** - Layout containers use `with` blocks
2. **Universal Isomorphism** - Layout is computed abstractly, rendered anywhere
3. **Atomic Reactivity** - Style changes trigger precise re-layout
4. **Native Leverage** - Use Python 3.14+ features (No-GIL for parallel layout)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flow Elements                            │
│   with Flex(direction="row", justify="center"):                 │
│       with Box(width=100, height=50):                           │
│           Text("Hello")                                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Layout Tree                                │
│   LayoutNode(style=FlexStyle, children=[...])                   │
│       - computed_layout: LayoutResult                           │
│       - Each node stores position/size after compute            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Flexbox Algorithm                             │
│   compute_layout(node, available_space) → LayoutResult          │
│       1. Resolve sizes (min/max/basis)                          │
│       2. Collect into flex lines                                │
│       3. Grow/shrink items                                      │
│       4. Align main axis (justify-content)                      │
│       5. Align cross axis (align-items/align-content)           │
│       6. Position absolutely-placed children                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RenderNode                                │
│   { tag: "div", props: { style: computed_css }, children }      │
│   Renderer receives computed positions for final output         │
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

### Task 1.5: LayoutNode and LayoutResult

**Files:**
- Create: `src/flow/layout/node.py`
- Test: `tests/test_layout_node.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_node.py
import pytest
from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import FlexStyle
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
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/node.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.style import FlexStyle

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

    # Computed layout (set after compute_layout)
    layout: LayoutResult = field(default_factory=LayoutResult)

    # Internal state for layout algorithm
    _dirty: bool = field(default=True, repr=False)

    def add_child(self, child: LayoutNode) -> None:
        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: LayoutNode) -> None:
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def mark_dirty(self) -> None:
        """Mark this node and ancestors as needing layout."""
        self._dirty = True
        if self.parent is not None:
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False
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

### Task 2.5: Flex Lines (Wrapping)

**Files:**
- Create: `src/flow/layout/flexline.py`
- Test: `tests/test_layout_flexline.py`

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
    """
    from flow.layout.style import FlexWrap

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
        gap_to_add = gap if current_line else 0
        if current_line and current_main + gap_to_add + item_main > container_main:
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
    resolve_flexible_lengths,
    distribute_justify_content,
    align_cross_axis,
)
from flow.layout.flexline import collect_flex_lines
from flow.layout.node import LayoutResult

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.types import Size

def compute_layout(node: LayoutNode, available: Size) -> None:
    """
    Compute layout for a node tree.

    This is the main entry point for the Flexbox algorithm.
    """
    # Resolve node's own size
    style = node.style

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

    # Layout children if any
    if node.children:
        _layout_children(node)

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

def _layout_children(node: LayoutNode) -> None:
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
        # Get main axis sizes
        main_sizes = resolve_flexible_lengths(
            items=line.items,
            container_main_size=container_main,
            direction=direction,
            gap=gap,
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

            # Recursively layout grandchildren
            if item.children:
                _layout_children(item)

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

### Task 3.3: Reactive Layout with Signals

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
    """A layout node with Signal-bound style properties."""

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
            unsub = signal.subscribe(self.mark_dirty)
            self._unsubscribes.append(unsub)

    def resolve_style(self) -> FlexStyle:
        """Get current style with Signal values resolved."""
        overrides = {
            name: signal.value
            for name, signal in self.style_signals.items()
        }
        return self.base_style.with_updates(**overrides)

    def mark_dirty(self) -> None:
        self._dirty = True
        if self.parent is not None:
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

### Task 5.5: No-GIL Parallel Layout

**Files:**
- Create: `src/flow/layout/parallel.py`
- Test: `tests/test_layout_parallel.py`

Implement parallel layout computation for No-GIL Python 3.14+:
- Compute independent subtrees in parallel
- Use ThreadPoolExecutor
- Measure performance gains

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| **1** | 1.1-1.5 | Core types: Dimension, Size, FlexStyle, LayoutNode |
| **2** | 2.1-2.6 | Flexbox algorithm: sizing, justify, align, wrap |
| **3** | 3.1-3.3 | Flow integration: Elements, Signals |
| **4** | 4.1-4.2 | Rendering: computed styles to HTML |
| **5** | 5.1-5.5 | Advanced: absolute, aspect ratio, parallel |

## Dependencies

- Python 3.14+ (for No-GIL parallel layout)
- Flow Framework (existing)
- No external layout libraries

## Success Criteria

1. All tests pass: `uv run pytest tests/test_layout*.py -v`
2. Demo works: `yoga_demo.py` from `yoga.md` renders correctly
3. Performance: Layout of 1000 nodes < 100ms

---

## Appendix: CSS Flexbox Specification References

- [CSS Flexible Box Layout Module Level 1](https://www.w3.org/TR/css-flexbox-1/)
- [9.2 Line Length Determination](https://www.w3.org/TR/css-flexbox-1/#algo-available)
- [9.3 Main Size Determination](https://www.w3.org/TR/css-flexbox-1/#algo-main-container)
- [9.4 Cross Size Determination](https://www.w3.org/TR/css-flexbox-1/#algo-cross-sizing)
- [9.5 Main-Axis Alignment](https://www.w3.org/TR/css-flexbox-1/#algo-main-align)
- [9.6 Cross-Axis Alignment](https://www.w3.org/TR/css-flexbox-1/#algo-cross-align)
