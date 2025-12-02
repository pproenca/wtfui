# Yoga Layout Parity - Gap Analysis & Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use super:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Achieve feature parity with Facebook Yoga layout engine for Flow's layout system

**Architecture:** Add missing CSS Flexbox features identified in Yoga's source code that our implementation lacks

**Tech Stack:** Python 3.14+, pytest, Flow Layout Engine

**Commands:** All Python commands use `uv run` prefix

---

## Gap Analysis Summary

After comparing Yoga's source code (`/tmp/yoga/yoga/`) with Flow's implementation (`src/flow/layout/`), the following gaps were identified:

### Features We Have ✅
- Core Flexbox: flex-direction, flex-wrap, justify-content, align-items, align-content
- Flex item properties: flex-grow, flex-shrink, flex-basis
- Sizing: width, height, min-width, min-height, max-width, max-height
- Spacing: margin, padding, gap (row_gap, column_gap)
- Positioning: position (relative, absolute), top/right/bottom/left insets
- Intrinsic sizing: min-content, max-content, fit-content
- Aspect ratio
- Layout boundaries (Amendment Gamma)
- MeasureFunc for text (Amendment Alpha)
- Style conflict resolution (Amendment Beta)
- Parallel layout computation
- Floating-point precision (LAYOUT_EPSILON)

### Features Missing ❌ (Yoga Has, We Don't)

| Feature | Yoga Location | Priority | Complexity |
|---------|---------------|----------|------------|
| **Direction (RTL/LTR)** | `enums/Direction.h` | HIGH | Medium |
| **Display (flex/none/contents)** | `enums/Display.h` | HIGH | Low |
| **Overflow (visible/hidden/scroll)** | `enums/Overflow.h` | MEDIUM | Low |
| **Position: Static** | `enums/PositionType.h` | MEDIUM | Low |
| **BoxSizing (border-box/content-box)** | `enums/BoxSizing.h` | HIGH | Medium |
| **Border widths** | `Style.h:border_` | HIGH | Medium |
| **Baseline alignment** | `algorithm/Baseline.cpp` | MEDIUM | High |
| **BaselineFunc callback** | `YGNode.h:hasBaselineFunc` | LOW | Medium |
| **Layout caching** | `algorithm/Cache.cpp` | MEDIUM | High |
| **Errata modes** | `enums/Errata.h` | LOW | Medium |
| **Align: SpaceEvenly for content** | `enums/Align.h` | LOW | Low |
| **Auto margins** | `Style.h:flexStartMarginIsAuto` | MEDIUM | Medium |

---

## Phase 1: High-Priority Missing Features

### Task 1.1: Add Display Enum

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.style import Display

class TestDisplay:
    def test_display_flex_default(self):
        """Flex is the default display mode."""
        assert Display.FLEX.value == "flex"
        assert Display.FLEX.is_visible()

    def test_display_none_hidden(self):
        """Display none hides the element."""
        assert Display.NONE.value == "none"
        assert not Display.NONE.is_visible()

    def test_display_contents(self):
        """Display contents makes element act as if replaced by children."""
        assert Display.CONTENTS.value == "contents"
        assert Display.CONTENTS.is_visible()
        assert Display.CONTENTS.is_contents()
```

**Step 2: Run test to verify it fails**
```bash
uv run pytest tests/test_layout_style.py::TestDisplay -v
```
Expected: FAIL with "cannot import name 'Display'"

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/style.py after Position enum

class Display(Enum):
    """Display mode for elements (matches Yoga's Display enum)."""

    FLEX = "flex"
    NONE = "none"
    CONTENTS = "contents"

    def is_visible(self) -> bool:
        """Check if element should be rendered."""
        return self != Display.NONE

    def is_contents(self) -> bool:
        """Check if element should act as if replaced by children."""
        return self == Display.CONTENTS
```

**Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_layout_style.py::TestDisplay -v
```
Expected: PASS

**Step 5: Commit**
```bash
git add src/flow/layout/style.py tests/test_layout_style.py
git commit -m "feat(layout): add Display enum (flex/none/contents) for Yoga parity"
```

---

### Task 1.2: Add Direction Enum (RTL/LTR Support)

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.style import Direction

class TestDirection:
    def test_direction_ltr_default(self):
        """LTR is the default direction."""
        assert Direction.LTR.value == "ltr"
        assert Direction.LTR.is_ltr()
        assert not Direction.LTR.is_rtl()

    def test_direction_rtl(self):
        """RTL reverses horizontal layout."""
        assert Direction.RTL.value == "rtl"
        assert Direction.RTL.is_rtl()
        assert not Direction.RTL.is_ltr()

    def test_direction_inherit(self):
        """Inherit takes direction from parent."""
        assert Direction.INHERIT.value == "inherit"
        assert not Direction.INHERIT.is_ltr()
        assert not Direction.INHERIT.is_rtl()
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/style.py

class Direction(Enum):
    """Text/layout direction (LTR or RTL)."""

    INHERIT = "inherit"
    LTR = "ltr"
    RTL = "rtl"

    def is_ltr(self) -> bool:
        """Check if left-to-right."""
        return self == Direction.LTR

    def is_rtl(self) -> bool:
        """Check if right-to-left."""
        return self == Direction.RTL
```

**Step 4: Run test, commit**
```bash
git commit -am "feat(layout): add Direction enum (LTR/RTL/inherit) for Yoga parity"
```

---

### Task 1.3: Add Overflow Enum

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.style import Overflow

class TestOverflow:
    def test_overflow_visible_default(self):
        """Visible is the default overflow mode."""
        assert Overflow.VISIBLE.value == "visible"
        assert Overflow.VISIBLE.allows_overflow()

    def test_overflow_hidden(self):
        """Hidden clips overflow content."""
        assert Overflow.HIDDEN.value == "hidden"
        assert not Overflow.HIDDEN.allows_overflow()

    def test_overflow_scroll(self):
        """Scroll adds scrollbars for overflow."""
        assert Overflow.SCROLL.value == "scroll"
        assert not Overflow.SCROLL.allows_overflow()
        assert Overflow.SCROLL.is_scrollable()
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/style.py

class Overflow(Enum):
    """Overflow behavior for elements."""

    VISIBLE = "visible"
    HIDDEN = "hidden"
    SCROLL = "scroll"

    def allows_overflow(self) -> bool:
        """Check if content can overflow the bounds."""
        return self == Overflow.VISIBLE

    def is_scrollable(self) -> bool:
        """Check if scrollbars should be shown."""
        return self == Overflow.SCROLL
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add Overflow enum (visible/hidden/scroll) for Yoga parity"
```

---

### Task 1.4: Add BoxSizing Enum

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.style import BoxSizing

class TestBoxSizing:
    def test_border_box_default(self):
        """Border-box is the default (width includes padding+border)."""
        assert BoxSizing.BORDER_BOX.value == "border-box"
        assert BoxSizing.BORDER_BOX.includes_padding()

    def test_content_box(self):
        """Content-box means width is content only."""
        assert BoxSizing.CONTENT_BOX.value == "content-box"
        assert not BoxSizing.CONTENT_BOX.includes_padding()
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/style.py

class BoxSizing(Enum):
    """Box sizing model (border-box or content-box)."""

    BORDER_BOX = "border-box"
    CONTENT_BOX = "content-box"

    def includes_padding(self) -> bool:
        """Check if padding is included in width/height."""
        return self == BoxSizing.BORDER_BOX
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add BoxSizing enum for Yoga parity"
```

---

### Task 1.5: Add Position.STATIC

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py

class TestPositionStatic:
    def test_position_static_exists(self):
        """Static position is in normal flow, ignores insets."""
        from flow.layout.style import Position
        assert Position.STATIC.value == "static"
        assert Position.STATIC.is_static()
        assert not Position.STATIC.is_positioned()

    def test_relative_is_positioned(self):
        from flow.layout.style import Position
        assert Position.RELATIVE.is_positioned()
        assert not Position.RELATIVE.is_static()

    def test_absolute_is_positioned(self):
        from flow.layout.style import Position
        assert Position.ABSOLUTE.is_positioned()
```

**Step 3: Write minimal implementation**
```python
# Modify Position enum in src/flow/layout/style.py

class Position(Enum):
    """Positioning mode for elements."""

    STATIC = "static"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"

    def is_static(self) -> bool:
        """Check if in normal flow (ignores insets)."""
        return self == Position.STATIC

    def is_positioned(self) -> bool:
        """Check if insets apply (relative or absolute)."""
        return self != Position.STATIC
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add Position.STATIC for Yoga parity"
```

---

### Task 1.6: Update FlexStyle with New Enums

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py

class TestFlexStyleNewEnums:
    def test_default_style_has_new_enums(self):
        from flow.layout.style import (
            FlexStyle, Display, Direction, Overflow, BoxSizing
        )
        style = FlexStyle()
        assert style.display == Display.FLEX
        assert style.direction == Direction.INHERIT
        assert style.overflow == Overflow.VISIBLE
        assert style.box_sizing == BoxSizing.BORDER_BOX

    def test_style_with_updates_new_enums(self):
        from flow.layout.style import (
            FlexStyle, Display, Direction, Overflow, BoxSizing
        )
        style = FlexStyle(
            display=Display.NONE,
            direction=Direction.RTL,
            overflow=Overflow.HIDDEN,
            box_sizing=BoxSizing.CONTENT_BOX,
        )
        assert style.display == Display.NONE
        assert style.direction == Direction.RTL
        assert style.overflow == Overflow.HIDDEN
        assert style.box_sizing == BoxSizing.CONTENT_BOX
```

**Step 3: Write minimal implementation**
```python
# Modify FlexStyle in src/flow/layout/style.py
# Add these fields after position field:

@dataclass(frozen=True, slots=True)
class FlexStyle:
    # ... existing fields ...

    # Display & Position
    display: Display = Display.FLEX  # NEW
    position: Position = Position.RELATIVE
    direction: Direction = Direction.INHERIT  # NEW
    overflow: Overflow = Overflow.VISIBLE  # NEW
    box_sizing: BoxSizing = BoxSizing.BORDER_BOX  # NEW

    # ... rest of existing fields ...
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add display, direction, overflow, box_sizing to FlexStyle"
```

---

## Phase 2: Border Support

### Task 2.1: Add Border Spacing Type

**Files:**
- Modify: `src/flow/layout/types.py`
- Modify: `tests/test_layout_types.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_types.py
from flow.layout.types import Border

class TestBorder:
    def test_border_all(self):
        """Create border with equal width on all sides."""
        border = Border.all(2)
        assert border.top == 2
        assert border.right == 2
        assert border.bottom == 2
        assert border.left == 2

    def test_border_resolve(self):
        """Border always resolves to its value (no percentage)."""
        border = Border(top=1, right=2, bottom=3, left=4)
        edges = border.resolve()
        assert edges.top == 1
        assert edges.right == 2
        assert edges.bottom == 3
        assert edges.left == 4

    def test_border_horizontal_vertical(self):
        border = Border(top=1, right=2, bottom=3, left=4)
        assert border.horizontal == 6  # left + right
        assert border.vertical == 4  # top + bottom
```

**Step 3: Write minimal implementation**
```python
# Add to src/flow/layout/types.py

@dataclass(frozen=True, slots=True)
class Border:
    """Border widths for each edge (always in points, not percentages)."""

    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> Border:
        """Create border with equal width on all sides."""
        return cls(value, value, value, value)

    @classmethod
    def zero(cls) -> Border:
        """Create zero border."""
        return cls(0, 0, 0, 0)

    @property
    def horizontal(self) -> float:
        """Sum of left and right borders."""
        return self.left + self.right

    @property
    def vertical(self) -> float:
        """Sum of top and bottom borders."""
        return self.top + self.bottom

    def resolve(self) -> Edges:
        """Convert to Edges (border is always concrete values)."""
        return Edges(
            top=self.top,
            right=self.right,
            bottom=self.bottom,
            left=self.left,
        )
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add Border type for Yoga parity"
```

---

### Task 2.2: Add Border to FlexStyle

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_style.py
from flow.layout.types import Border

class TestFlexStyleBorder:
    def test_default_style_has_zero_border(self):
        style = FlexStyle()
        assert style.border.top == 0
        assert style.border.horizontal == 0

    def test_style_with_border(self):
        style = FlexStyle(border=Border.all(2))
        assert style.border.top == 2
        assert style.border.horizontal == 4
```

**Step 3: Write minimal implementation**
```python
# Add to FlexStyle in src/flow/layout/style.py

from flow.layout.types import Border

@dataclass(frozen=True, slots=True)
class FlexStyle:
    # ... existing fields ...

    # Spacing
    margin: Spacing = field(default_factory=Spacing)
    padding: Spacing = field(default_factory=Spacing)
    border: Border = field(default_factory=Border.zero)  # NEW
    gap: float = 0.0
    # ...
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add border to FlexStyle"
```

---

### Task 2.3: Update compute_layout for Border

**Files:**
- Modify: `src/flow/layout/compute.py`
- Modify: `tests/test_layout_compute.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_compute.py
from flow.layout.compute import compute_layout
from flow.layout.node import LayoutNode
from flow.layout.style import FlexStyle
from flow.layout.types import Size, Dimension, Border

class TestComputeLayoutBorder:
    def test_border_reduces_content_area(self):
        """Border reduces available space for children."""
        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
                border=Border.all(10),
            )
        )
        child = LayoutNode(
            style=FlexStyle(flex_grow=1.0)
        )
        parent.add_child(child)

        compute_layout(parent, Size(100, 100))

        # Parent is 100x100
        assert parent.layout.width == 100
        assert parent.layout.height == 100

        # Child should be 80x80 (100 - 10*2 border on each side)
        assert child.layout.width == 80
        assert child.layout.height == 80
        # Child positioned inside border
        assert child.layout.x == 10
        assert child.layout.y == 10
```

**Step 3: Write minimal implementation**
```python
# Modify _layout_children in src/flow/layout/compute.py

def _layout_children(node: LayoutNode) -> None:
    """Layout children using Flexbox algorithm."""
    style = node.style
    direction = style.flex_direction
    is_row = direction.is_row()

    # Get container inner size (subtract padding AND border)
    padding = style.padding.resolve(node.layout.width, node.layout.height)
    border = style.border.resolve()  # NEW

    inner_width = node.layout.width - padding.horizontal - border.horizontal
    inner_height = node.layout.height - padding.vertical - border.vertical

    # ... rest of layout logic ...

    # When positioning items, offset by border + padding
    for line_idx, line in enumerate(lines):
        # ...
        cross_offset = (
            (padding.top + border.top) if is_row else (padding.left + border.left)
        ) + line_offsets[line_idx]

        for i, item in enumerate(line.items):
            # ...
            if is_row:
                x = padding.left + border.left + main_pos  # Include border
                y = cross_offset + cross_pos
                # ...
            else:
                x = cross_offset + cross_pos
                y = padding.top + border.top + main_pos  # Include border
                # ...
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): include border in layout calculation"
```

---

## Phase 3: Display None Support

### Task 3.1: Skip Hidden Elements in Layout

**Files:**
- Modify: `src/flow/layout/compute.py`
- Modify: `tests/test_layout_compute.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_compute.py

class TestDisplayNone:
    def test_display_none_skipped_in_layout(self):
        """Elements with display:none don't participate in layout."""
        from flow.layout.style import Display

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        visible_child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        hidden_child = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                width=Dimension.points(50),
            )
        )
        visible_child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        parent.add_child(visible_child)
        parent.add_child(hidden_child)
        parent.add_child(visible_child2)

        compute_layout(parent, Size(200, 100))

        # Hidden child has zero size
        assert hidden_child.layout.width == 0
        assert hidden_child.layout.height == 0

        # Visible children split the full width (not affected by hidden)
        assert visible_child.layout.width == 100
        assert visible_child2.layout.width == 100
```

**Step 3: Write minimal implementation**
```python
# Modify _layout_children in src/flow/layout/compute.py

def _layout_children(node: LayoutNode) -> None:
    # ...

    # Separate flex items, filtering out display:none
    flex_items: list[LayoutNode] = []
    absolute_items: list[LayoutNode] = []
    hidden_items: list[LayoutNode] = []  # NEW

    for child in node.children:
        if child.style.display == Display.NONE:  # NEW
            hidden_items.append(child)
        elif child.style.position == Position.ABSOLUTE:
            absolute_items.append(child)
        else:
            flex_items.append(child)

    # ... layout flex_items and absolute_items ...

    # Set hidden items to zero size  # NEW
    for hidden in hidden_items:
        hidden.layout = LayoutResult(x=0, y=0, width=0, height=0)
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): skip display:none elements in layout"
```

---

## Phase 4: RTL Direction Support

### Task 4.1: Resolve Direction in FlexDirection

**Files:**
- Create: `src/flow/layout/direction.py`
- Test: `tests/test_layout_direction.py`

**Step 1: Write the failing test**
```python
# tests/test_layout_direction.py
from flow.layout.direction import resolve_flex_direction
from flow.layout.style import FlexDirection, Direction

class TestResolveFlexDirection:
    def test_row_ltr_unchanged(self):
        """Row in LTR stays row."""
        result = resolve_flex_direction(FlexDirection.ROW, Direction.LTR)
        assert result == FlexDirection.ROW

    def test_row_rtl_becomes_row_reverse(self):
        """Row in RTL becomes row-reverse."""
        result = resolve_flex_direction(FlexDirection.ROW, Direction.RTL)
        assert result == FlexDirection.ROW_REVERSE

    def test_row_reverse_rtl_becomes_row(self):
        """Row-reverse in RTL becomes row."""
        result = resolve_flex_direction(FlexDirection.ROW_REVERSE, Direction.RTL)
        assert result == FlexDirection.ROW

    def test_column_rtl_unchanged(self):
        """Column is not affected by RTL."""
        result = resolve_flex_direction(FlexDirection.COLUMN, Direction.RTL)
        assert result == FlexDirection.COLUMN
```

**Step 3: Write minimal implementation**
```python
# src/flow/layout/direction.py
"""Direction resolution for RTL/LTR support (matches Yoga's FlexDirection.h)."""

from __future__ import annotations

from flow.layout.style import Direction, FlexDirection


def resolve_flex_direction(
    flex_direction: FlexDirection,
    direction: Direction,
) -> FlexDirection:
    """Resolve flex direction based on layout direction (LTR/RTL).

    In RTL mode, row and row-reverse are swapped.
    Column directions are unaffected.

    Args:
        flex_direction: The flex-direction style property.
        direction: The layout direction (LTR or RTL).

    Returns:
        The resolved flex direction.
    """
    if direction == Direction.RTL:
        if flex_direction == FlexDirection.ROW:
            return FlexDirection.ROW_REVERSE
        if flex_direction == FlexDirection.ROW_REVERSE:
            return FlexDirection.ROW

    return flex_direction
```

**Step 4-5: Run test, commit**
```bash
git add src/flow/layout/direction.py tests/test_layout_direction.py
git commit -m "feat(layout): add resolve_flex_direction for RTL support"
```

---

### Task 4.2: Apply Direction in compute_layout

**Files:**
- Modify: `src/flow/layout/compute.py`
- Modify: `tests/test_layout_compute.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_compute.py

class TestRTLLayout:
    def test_row_rtl_reverses_children(self):
        """Row direction in RTL lays out children right-to-left."""
        from flow.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                direction=Direction.RTL,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(300, 100))

        # In RTL, first child is on the right
        assert child1.layout.x == 200  # 300 - 100
        assert child2.layout.x == 100  # 300 - 100 - 100
```

**Step 3: Write minimal implementation**
```python
# Modify _layout_children in src/flow/layout/compute.py

from flow.layout.direction import resolve_flex_direction

def _layout_children(node: LayoutNode) -> None:
    style = node.style

    # Resolve direction for RTL support
    resolved_direction = resolve_flex_direction(
        style.flex_direction,
        style.direction,
    )

    is_row = resolved_direction.is_row()
    is_reversed = resolved_direction.is_reverse()

    # ... use resolved_direction instead of style.flex_direction ...
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): apply RTL direction in compute_layout"
```

---

## Phase 5: Auto Margins Support

### Task 5.1: Detect Auto Margins

**Files:**
- Modify: `src/flow/layout/types.py`
- Modify: `tests/test_layout_types.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_types.py

class TestSpacingAutoMargin:
    def test_spacing_has_auto_check(self):
        """Spacing can detect if any edge is auto."""
        auto_left = Spacing(
            top=Dimension.points(0),
            right=Dimension.points(0),
            bottom=Dimension.points(0),
            left=Dimension.auto(),
        )
        assert auto_left.left_is_auto()
        assert not auto_left.right_is_auto()

    def test_spacing_both_horizontal_auto(self):
        """Detect when both horizontal margins are auto (centering)."""
        centered = Spacing(
            top=Dimension.points(0),
            right=Dimension.auto(),
            bottom=Dimension.points(0),
            left=Dimension.auto(),
        )
        assert centered.horizontal_is_auto()
```

**Step 3: Write minimal implementation**
```python
# Add to Spacing in src/flow/layout/types.py

@dataclass(frozen=True, slots=True)
class Spacing:
    # ... existing fields and methods ...

    def left_is_auto(self) -> bool:
        """Check if left margin is auto."""
        return self.left is not None and self.left.is_auto()

    def right_is_auto(self) -> bool:
        """Check if right margin is auto."""
        return self.right is not None and self.right.is_auto()

    def top_is_auto(self) -> bool:
        """Check if top margin is auto."""
        return self.top is not None and self.top.is_auto()

    def bottom_is_auto(self) -> bool:
        """Check if bottom margin is auto."""
        return self.bottom is not None and self.bottom.is_auto()

    def horizontal_is_auto(self) -> bool:
        """Check if both horizontal margins are auto."""
        return self.left_is_auto() and self.right_is_auto()

    def vertical_is_auto(self) -> bool:
        """Check if both vertical margins are auto."""
        return self.top_is_auto() and self.bottom_is_auto()
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): add auto margin detection to Spacing"
```

---

### Task 5.2: Apply Auto Margins in Layout

**Files:**
- Modify: `src/flow/layout/algorithm.py`
- Modify: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**
```python
# Add to tests/test_layout_algorithm.py

class TestAutoMargins:
    def test_auto_margin_left_pushes_right(self):
        """Auto margin on left pushes item to the right."""
        from flow.layout.types import Spacing, Dimension

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.points(0),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child pushed to the right by auto margin
        assert child.layout.x == 150  # 200 - 50

    def test_auto_margins_both_centers(self):
        """Auto margins on both sides centers the item."""
        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.x == 75
```

**Step 3: Update algorithm to apply auto margins**

Auto margins absorb free space before justify-content is applied.

```python
# Modify distribute_justify_content in src/flow/layout/algorithm.py
# to accept margin info and handle auto margins

def apply_auto_margins(
    items: list[LayoutNode],
    positions: list[float],
    sizes: list[float],
    container_size: float,
    is_row: bool,
) -> list[float]:
    """Adjust positions for auto margins (absorbs free space)."""
    if not items:
        return positions

    adjusted = list(positions)

    for i, item in enumerate(items):
        margin = item.style.margin
        size = sizes[i]

        if is_row:
            left_auto = margin.left_is_auto()
            right_auto = margin.right_is_auto()

            if left_auto and right_auto:
                # Center: distribute remaining space equally
                remaining = container_size - size
                adjusted[i] = remaining / 2
            elif left_auto:
                # Push to the right
                adjusted[i] = container_size - size
            # right_auto alone doesn't change position
        else:
            top_auto = margin.top_is_auto()
            bottom_auto = margin.bottom_is_auto()

            if top_auto and bottom_auto:
                remaining = container_size - size
                adjusted[i] = remaining / 2
            elif top_auto:
                adjusted[i] = container_size - size

    return adjusted
```

**Step 4-5: Run test, commit**
```bash
git commit -am "feat(layout): implement auto margins for Yoga parity"
```

---

## Summary of All Tasks

| Phase | Task | Description | Files |
|-------|------|-------------|-------|
| 1 | 1.1 | Add Display enum | style.py |
| 1 | 1.2 | Add Direction enum (RTL/LTR) | style.py |
| 1 | 1.3 | Add Overflow enum | style.py |
| 1 | 1.4 | Add BoxSizing enum | style.py |
| 1 | 1.5 | Add Position.STATIC | style.py |
| 1 | 1.6 | Update FlexStyle with new enums | style.py |
| 2 | 2.1 | Add Border type | types.py |
| 2 | 2.2 | Add border to FlexStyle | style.py |
| 2 | 2.3 | Update compute_layout for border | compute.py |
| 3 | 3.1 | Skip display:none in layout | compute.py |
| 4 | 4.1 | Create direction resolver | direction.py |
| 4 | 4.2 | Apply direction in compute | compute.py |
| 5 | 5.1 | Add auto margin detection | types.py |
| 5 | 5.2 | Apply auto margins in layout | algorithm.py |

---

## Future Enhancements (Lower Priority)

These features exist in Yoga but are lower priority for initial parity:

1. **Baseline alignment** - Requires text metrics callback
2. **Layout caching** - Performance optimization
3. **Errata modes** - Compatibility with older Yoga versions
4. **BaselineFunc callback** - For custom baseline calculation

---

## Verification

After implementing all tasks, run full test suite:

```bash
uv run pytest tests/test_layout*.py -v
```

All tests should pass, confirming Yoga parity for the high-priority features.
