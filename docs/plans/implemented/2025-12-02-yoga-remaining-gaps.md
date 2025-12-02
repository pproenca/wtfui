# Yoga Layout Parity - Remaining Gaps Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use super:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Complete Yoga parity by implementing remaining features from the gap analysis

**Architecture:** Add missing align-content value, baseline alignment, and layout caching for performance

**Tech Stack:** Python 3.14+, pytest, Flow Layout Engine

**Commands:** All Python commands use `uv run` prefix

---

## Current Status

### Already Implemented ✅ (233 tests passing)

From `2025-12-02-yoga-layout.md`:
- Core Flexbox algorithm (direction, wrap, justify, align-items, align-content)
- Flex item properties (grow, shrink, basis)
- Sizing (width, height, min/max constraints)
- Spacing (margin, padding, gap)
- Positioning (relative, absolute)
- Intrinsic sizing (min-content, max-content, fit-content)
- Aspect ratio
- MeasureFunc protocol (Amendment Alpha)
- Style vs. prop conflict resolution (Amendment Beta)
- Layout boundaries and parallel computation (Amendment Gamma)
- Floating-point precision (LAYOUT_EPSILON)

From `2025-12-02-yoga-parity-gaps.md`:
- Display enum (flex/none/contents)
- Direction enum (LTR/RTL/inherit)
- Overflow enum (visible/hidden/scroll)
- BoxSizing enum (border-box/content-box)
- Position.STATIC
- Border type and layout integration
- RTL direction resolution
- Auto margins

### Remaining Gaps ❌

| Feature | Yoga Location | Priority | Complexity |
|---------|---------------|----------|------------|
| **AlignContent.SPACE_EVENLY** | `enums/Align.h` | HIGH | Low |
| **Baseline alignment** | `algorithm/Baseline.cpp` | MEDIUM | Medium |
| **BaselineFunc callback** | `YGNode.h:hasBaselineFunc` | MEDIUM | Low |
| **Layout caching** | `algorithm/Cache.cpp` | LOW | High |

---

## Phase 1: Complete Align Values

### Task 1.1: Add AlignContent.SPACE_EVENLY

**Files:**
- Modify: `src/flow/layout/style.py`
- Modify: `tests/test_layout_style.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_style.py
from flow.layout.style import AlignContent

class TestAlignContentSpaceEvenly:
    def test_space_evenly_exists(self):
        """AlignContent.SPACE_EVENLY distributes space evenly."""
        assert AlignContent.SPACE_EVENLY.value == "space-evenly"

    def test_all_align_content_values(self):
        """Verify all align-content values match Yoga's Align enum."""
        values = [ac.value for ac in AlignContent]
        assert "flex-start" in values
        assert "flex-end" in values
        assert "center" in values
        assert "stretch" in values
        assert "space-between" in values
        assert "space-around" in values
        assert "space-evenly" in values  # NEW
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_layout_style.py::TestAlignContentSpaceEvenly -v
```
Expected: FAIL with "AttributeError: SPACE_EVENLY"

**Step 3: Write minimal implementation**

```python
# Modify AlignContent in src/flow/layout/style.py

class AlignContent(Enum):
    """Cross axis alignment for flex lines (multi-line)."""

    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"  # NEW - matches Yoga's Align::SpaceEvenly
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_style.py::TestAlignContentSpaceEvenly -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/layout/style.py tests/test_layout_style.py
git commit -m "feat(layout): add AlignContent.SPACE_EVENLY for Yoga parity"
```

---

### Task 1.2: Implement SPACE_EVENLY in align_cross_axis

**Files:**
- Modify: `src/flow/layout/algorithm.py`
- Modify: `tests/test_layout_algorithm.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_algorithm.py
from flow.layout.algorithm import align_cross_lines
from flow.layout.style import AlignContent

class TestAlignContentSpaceEvenly:
    def test_space_evenly_distribution(self):
        """SPACE_EVENLY distributes space evenly between, before, and after lines."""
        line_sizes = [50, 50]  # Two lines, 50px each
        container_size = 200   # Container is 200px
        # Free space = 200 - 100 = 100px
        # SPACE_EVENLY: 100 / 3 = 33.33... between each gap
        # Line 1 starts at 33.33, Line 2 starts at 33.33 + 50 + 33.33 = 116.66

        offsets = align_cross_lines(
            line_sizes=line_sizes,
            container_cross_size=container_size,
            align_content=AlignContent.SPACE_EVENLY,
        )

        # 3 gaps (before, between, after) = 100 / 3 = 33.33...
        assert len(offsets) == 2
        assert abs(offsets[0] - 33.333) < 0.01
        assert abs(offsets[1] - 116.666) < 0.01

    def test_space_evenly_single_line(self):
        """SPACE_EVENLY with single line centers it."""
        line_sizes = [50]
        container_size = 200
        # Free space = 150, 2 gaps (before and after), 150/2 = 75

        offsets = align_cross_lines(
            line_sizes=line_sizes,
            container_cross_size=container_size,
            align_content=AlignContent.SPACE_EVENLY,
        )

        assert len(offsets) == 1
        assert offsets[0] == 75  # Centered
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_layout_algorithm.py::TestAlignContentSpaceEvenly -v
```

**Step 3: Write minimal implementation**

```python
# Modify align_cross_lines in src/flow/layout/algorithm.py

def align_cross_lines(
    line_sizes: list[float],
    container_cross_size: float,
    align_content: AlignContent,
) -> list[float]:
    """Calculate cross-axis offset for each flex line."""
    total_line_size = sum(line_sizes)
    free_space = container_cross_size - total_line_size
    num_lines = len(line_sizes)

    if num_lines == 0:
        return []

    offsets: list[float] = []
    current_offset = 0.0

    if align_content == AlignContent.FLEX_START:
        pass  # current_offset stays 0
    elif align_content == AlignContent.FLEX_END:
        current_offset = free_space
    elif align_content == AlignContent.CENTER:
        current_offset = free_space / 2
    elif align_content == AlignContent.SPACE_BETWEEN:
        gap = free_space / (num_lines - 1) if num_lines > 1 else 0
        for i, line_size in enumerate(line_sizes):
            offsets.append(current_offset)
            current_offset += line_size + gap
        return offsets
    elif align_content == AlignContent.SPACE_AROUND:
        margin = free_space / (num_lines * 2)
        current_offset = margin
        for i, line_size in enumerate(line_sizes):
            offsets.append(current_offset)
            current_offset += line_size + margin * 2
        return offsets
    elif align_content == AlignContent.SPACE_EVENLY:  # NEW
        # Distribute free space evenly between all gaps (including before first and after last)
        num_gaps = num_lines + 1
        gap = free_space / num_gaps if num_gaps > 0 else 0
        current_offset = gap
        for line_size in line_sizes:
            offsets.append(current_offset)
            current_offset += line_size + gap
        return offsets
    elif align_content == AlignContent.STRETCH:
        # Stretch lines to fill available space
        extra_per_line = free_space / num_lines if num_lines > 0 else 0
        for line_size in line_sizes:
            offsets.append(current_offset)
            current_offset += line_size + extra_per_line
        return offsets

    # Default path for FLEX_START, FLEX_END, CENTER
    for line_size in line_sizes:
        offsets.append(current_offset)
        current_offset += line_size

    return offsets
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_algorithm.py::TestAlignContentSpaceEvenly -v
```

**Step 5: Commit**

```bash
git commit -am "feat(layout): implement AlignContent.SPACE_EVENLY in cross-axis alignment"
```

---

## Phase 2: Baseline Alignment

### Task 2.1: Add BaselineFunc Protocol

**Files:**
- Modify: `src/flow/layout/node.py`
- Create: `tests/test_layout_baseline.py`

**Step 1: Write the failing test**

```python
# tests/test_layout_baseline.py
import pytest
from flow.layout.node import LayoutNode, BaselineFunc
from flow.layout.style import FlexStyle
from flow.layout.types import Dimension

class TestBaselineFunc:
    def test_baseline_func_protocol(self):
        """BaselineFunc takes width/height and returns baseline offset from top."""
        def my_baseline(width: float, height: float) -> float:
            # Typical text baseline: 80% from top (20% descender)
            return height * 0.8

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
            baseline_func=my_baseline,
        )

        assert node.has_baseline_func()
        baseline = node.get_baseline(100, 50)
        assert baseline == 40.0  # 50 * 0.8

    def test_node_without_baseline_func(self):
        """Node without baseline_func returns None."""
        node = LayoutNode(style=FlexStyle())
        assert not node.has_baseline_func()
        assert node.get_baseline(100, 50) is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_layout_baseline.py::TestBaselineFunc -v
```

**Step 3: Write minimal implementation**

```python
# Add to src/flow/layout/node.py

from typing import Callable, Protocol

class BaselineFunc(Protocol):
    """Protocol for baseline calculation callback.

    Returns the baseline offset from the top of the element.
    Typical use: text elements return baseline = height - descender.
    """
    def __call__(self, width: float, height: float) -> float: ...


@dataclass
class LayoutNode:
    """A node in the layout tree."""

    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    layout: LayoutResult = field(default_factory=LayoutResult)
    measure_func: MeasureFunc | None = None
    baseline_func: BaselineFunc | None = None  # NEW

    def has_baseline_func(self) -> bool:
        """Check if this node has a custom baseline function."""
        return self.baseline_func is not None

    def get_baseline(self, width: float, height: float) -> float | None:
        """Get the baseline offset from top, or None if no baseline_func."""
        if self.baseline_func is not None:
            return self.baseline_func(width, height)
        return None
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_baseline.py::TestBaselineFunc -v
```

**Step 5: Commit**

```bash
git add src/flow/layout/node.py tests/test_layout_baseline.py
git commit -m "feat(layout): add BaselineFunc protocol for baseline alignment"
```

---

### Task 2.2: Implement calculate_baseline Function

**Files:**
- Create: `src/flow/layout/baseline.py`
- Modify: `tests/test_layout_baseline.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_baseline.py
from flow.layout.baseline import calculate_baseline, is_baseline_layout
from flow.layout.style import FlexDirection, AlignItems

class TestCalculateBaseline:
    def test_baseline_from_baseline_func(self):
        """Node with baseline_func uses it directly."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
            baseline_func=lambda w, h: h * 0.8,
        )
        node.layout = LayoutResult(x=0, y=0, width=100, height=50)

        baseline = calculate_baseline(node)
        assert baseline == 40.0

    def test_baseline_from_first_child(self):
        """Node without baseline_func uses first child's baseline."""
        child = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)),
            baseline_func=lambda w, h: h * 0.8,  # 24
        )
        child.layout = LayoutResult(x=10, y=5, width=50, height=30)

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
        )
        parent.add_child(child)
        parent.layout = LayoutResult(x=0, y=0, width=100, height=50)

        # Baseline = child.y + child baseline = 5 + 24 = 29
        baseline = calculate_baseline(parent)
        assert baseline == 29.0

    def test_baseline_no_children_uses_height(self):
        """Node without baseline_func or children uses its own height."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            ),
        )
        node.layout = LayoutResult(x=0, y=0, width=100, height=50)

        baseline = calculate_baseline(node)
        assert baseline == 50.0


class TestIsBaselineLayout:
    def test_row_with_align_baseline(self):
        """Row with align-items: baseline is baseline layout."""
        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            ),
        )
        assert is_baseline_layout(node)

    def test_column_never_baseline(self):
        """Column direction is never baseline layout."""
        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.COLUMN,
                align_items=AlignItems.BASELINE,
            ),
        )
        assert not is_baseline_layout(node)

    def test_row_without_baseline_alignment(self):
        """Row with non-baseline alignment is not baseline layout."""
        node = LayoutNode(
            style=FlexStyle(
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.CENTER,
            ),
        )
        assert not is_baseline_layout(node)
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

```python
# src/flow/layout/baseline.py
"""Baseline alignment calculation (matches Yoga's algorithm/Baseline.cpp)."""

from __future__ import annotations

from flow.layout.node import LayoutNode
from flow.layout.style import AlignItems, Position


def calculate_baseline(node: LayoutNode) -> float:
    """Calculate the baseline of a node.

    If the node has a baseline_func, use it.
    Otherwise, recursively find the baseline from the first appropriate child.
    If no baseline can be found, return the node's height.

    Args:
        node: The layout node to calculate baseline for.

    Returns:
        The baseline offset from the top of the node.
    """
    # If node has explicit baseline function, use it
    if node.has_baseline_func():
        return node.baseline_func(node.layout.width, node.layout.height)

    # Find first child that qualifies for baseline
    baseline_child: LayoutNode | None = None

    for child in node.children:
        # Skip absolute positioned children
        if child.style.position == Position.ABSOLUTE:
            continue

        # Prefer children with align-self: baseline
        effective_align = child.style.align_self or node.style.align_items
        if effective_align == AlignItems.BASELINE:
            baseline_child = child
            break

        # Otherwise use first non-absolute child
        if baseline_child is None:
            baseline_child = child

    if baseline_child is None:
        # No suitable child found, use own height
        return node.layout.height

    # Recursively get child's baseline and add its y position
    child_baseline = calculate_baseline(baseline_child)
    return child_baseline + baseline_child.layout.y


def is_baseline_layout(node: LayoutNode) -> bool:
    """Check if this node uses baseline alignment.

    Baseline alignment only applies to row direction (horizontal).
    Returns True if align-items is baseline or any child has align-self baseline.

    Args:
        node: The layout node to check.

    Returns:
        True if baseline alignment should be used.
    """
    # Baseline only applies to row direction
    if node.style.flex_direction.is_column():
        return False

    # Check if container uses baseline alignment
    if node.style.align_items == AlignItems.BASELINE:
        return True

    # Check if any child uses align-self: baseline
    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            continue
        if child.style.align_self == AlignItems.BASELINE:
            return True

    return False
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_baseline.py -v
```

**Step 5: Commit**

```bash
git add src/flow/layout/baseline.py tests/test_layout_baseline.py
git commit -m "feat(layout): add calculate_baseline and is_baseline_layout"
```

---

### Task 2.3: Integrate Baseline in Cross-Axis Alignment

**Files:**
- Modify: `src/flow/layout/compute.py`
- Modify: `tests/test_layout_compute.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_compute.py
from flow.layout.compute import compute_layout
from flow.layout.style import AlignItems

class TestBaselineAlignment:
    def test_baseline_alignment_row(self):
        """Items with baseline alignment align on their baselines."""
        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            )
        )

        # Small text (baseline at 80% of height)
        small_text = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(20)),
            baseline_func=lambda w, h: h * 0.8,  # baseline at 16
        )

        # Large text (baseline at 80% of height)
        large_text = LayoutNode(
            style=FlexStyle(width=Dimension.points(100), height=Dimension.points(40)),
            baseline_func=lambda w, h: h * 0.8,  # baseline at 32
        )

        parent.add_child(small_text)
        parent.add_child(large_text)

        compute_layout(parent, Size(300, 100))

        # Both baselines should align
        # Large text baseline = y + 32
        # Small text baseline = y + 16
        # For baselines to align: small_y + 16 = large_y + 32
        # If large_text.y = 0, then small_text.y = 16

        small_baseline = small_text.layout.y + 16
        large_baseline = large_text.layout.y + 32

        assert abs(small_baseline - large_baseline) < 0.01

    def test_baseline_with_align_self_override(self):
        """Child with align-self overrides parent's baseline alignment."""
        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                align_items=AlignItems.BASELINE,
            )
        )

        baseline_child = LayoutNode(
            style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)),
            baseline_func=lambda w, h: h * 0.8,
        )

        centered_child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                height=Dimension.points(30),
                align_self=AlignItems.CENTER,  # Override
            ),
        )

        parent.add_child(baseline_child)
        parent.add_child(centered_child)

        compute_layout(parent, Size(200, 100))

        # Centered child should be at (100 - 30) / 2 = 35
        assert abs(centered_child.layout.y - 35) < 0.01
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

```python
# Modify _layout_children in src/flow/layout/compute.py

from flow.layout.baseline import calculate_baseline, is_baseline_layout

def _align_items_in_line(
    items: list[LayoutNode],
    line_cross_size: float,
    align_items: AlignItems,
    is_row: bool,
    container_node: LayoutNode,
) -> list[float]:
    """Calculate cross-axis positions for items in a flex line.

    For baseline alignment, find the maximum baseline and align items on it.
    """
    positions: list[float] = []

    # Check if this is baseline layout
    use_baseline = is_baseline_layout(container_node)

    if use_baseline and is_row:
        # Find maximum baseline in this line
        max_baseline = 0.0
        baselines: list[float] = []

        for item in items:
            effective_align = item.style.align_self or align_items
            if effective_align == AlignItems.BASELINE:
                baseline = calculate_baseline(item)
                baselines.append(baseline)
                max_baseline = max(max_baseline, baseline)
            else:
                baselines.append(-1)  # Marker for non-baseline items

        for i, item in enumerate(items):
            effective_align = item.style.align_self or align_items
            item_size = item.layout.height if is_row else item.layout.width

            if effective_align == AlignItems.BASELINE and baselines[i] >= 0:
                # Align on baseline: position = max_baseline - item_baseline
                positions.append(max_baseline - baselines[i])
            elif effective_align == AlignItems.FLEX_START:
                positions.append(0)
            elif effective_align == AlignItems.FLEX_END:
                positions.append(line_cross_size - item_size)
            elif effective_align == AlignItems.CENTER:
                positions.append((line_cross_size - item_size) / 2)
            elif effective_align == AlignItems.STRETCH:
                positions.append(0)
            else:
                positions.append(0)

        return positions

    # Non-baseline alignment (existing logic)
    for item in items:
        effective_align = item.style.align_self or align_items
        item_size = item.layout.height if is_row else item.layout.width

        if effective_align == AlignItems.FLEX_START:
            positions.append(0)
        elif effective_align == AlignItems.FLEX_END:
            positions.append(line_cross_size - item_size)
        elif effective_align == AlignItems.CENTER:
            positions.append((line_cross_size - item_size) / 2)
        elif effective_align == AlignItems.STRETCH:
            positions.append(0)
        elif effective_align == AlignItems.BASELINE:
            # Baseline without baseline layout context: treat as flex-start
            positions.append(0)
        else:
            positions.append(0)

    return positions
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_compute.py::TestBaselineAlignment -v
```

**Step 5: Commit**

```bash
git commit -am "feat(layout): integrate baseline alignment in compute_layout"
```

---

## Phase 3: Layout Caching (Performance Optimization)

### Task 3.1: Add CachedMeasurement to LayoutNode

**Files:**
- Modify: `src/flow/layout/node.py`
- Create: `tests/test_layout_cache.py`

**Step 1: Write the failing test**

```python
# tests/test_layout_cache.py
import pytest
from flow.layout.node import LayoutNode, CachedMeasurement
from flow.layout.style import FlexStyle
from flow.layout.types import Dimension
from flow.layout.intrinsic import SizingMode

class TestCachedMeasurement:
    def test_cached_measurement_dataclass(self):
        """CachedMeasurement stores sizing parameters and result."""
        cache = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=SizingMode.EXACTLY,
            height_mode=SizingMode.AT_MOST,
            computed_width=100,
            computed_height=150,
        )
        assert cache.available_width == 100
        assert cache.computed_width == 100

    def test_node_has_cached_measurement(self):
        """LayoutNode can store cached measurement."""
        node = LayoutNode(style=FlexStyle())
        assert node.cached_measurement is None

        node.cached_measurement = CachedMeasurement(
            available_width=100,
            available_height=200,
            width_mode=SizingMode.EXACTLY,
            height_mode=SizingMode.AT_MOST,
            computed_width=100,
            computed_height=150,
        )
        assert node.cached_measurement is not None
        assert node.cached_measurement.computed_width == 100
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

```python
# Add to src/flow/layout/node.py

@dataclass
class CachedMeasurement:
    """Cached layout measurement for avoiding redundant calculations.

    Matches Yoga's cache invalidation logic.
    """
    available_width: float
    available_height: float
    width_mode: SizingMode
    height_mode: SizingMode
    computed_width: float
    computed_height: float


@dataclass
class LayoutNode:
    """A node in the layout tree."""

    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    layout: LayoutResult = field(default_factory=LayoutResult)
    measure_func: MeasureFunc | None = None
    baseline_func: BaselineFunc | None = None
    cached_measurement: CachedMeasurement | None = None  # NEW

    def invalidate_cache(self) -> None:
        """Clear cached measurement for this node."""
        self.cached_measurement = None
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add src/flow/layout/node.py tests/test_layout_cache.py
git commit -m "feat(layout): add CachedMeasurement dataclass to LayoutNode"
```

---

### Task 3.2: Implement can_use_cached_measurement

**Files:**
- Create: `src/flow/layout/cache.py`
- Modify: `tests/test_layout_cache.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_cache.py
from flow.layout.cache import can_use_cached_measurement

class TestCanUseCachedMeasurement:
    def test_exact_match_uses_cache(self):
        """Exact same sizing parameters uses cache."""
        result = can_use_cached_measurement(
            width_mode=SizingMode.EXACTLY,
            available_width=100,
            height_mode=SizingMode.AT_MOST,
            available_height=200,
            last_width_mode=SizingMode.EXACTLY,
            last_available_width=100,
            last_height_mode=SizingMode.AT_MOST,
            last_available_height=200,
            last_computed_width=100,
            last_computed_height=150,
        )
        assert result is True

    def test_different_width_invalidates(self):
        """Different available width invalidates cache."""
        result = can_use_cached_measurement(
            width_mode=SizingMode.EXACTLY,
            available_width=150,  # Different
            height_mode=SizingMode.AT_MOST,
            available_height=200,
            last_width_mode=SizingMode.EXACTLY,
            last_available_width=100,
            last_height_mode=SizingMode.AT_MOST,
            last_available_height=200,
            last_computed_width=100,
            last_computed_height=150,
        )
        assert result is False

    def test_fit_content_reuses_if_still_fits(self):
        """FIT_CONTENT mode can reuse cache if content still fits."""
        result = can_use_cached_measurement(
            width_mode=SizingMode.FIT_CONTENT,
            available_width=200,  # Larger available
            height_mode=SizingMode.EXACTLY,
            available_height=100,
            last_width_mode=SizingMode.MAX_CONTENT,
            last_available_width=float('inf'),
            last_height_mode=SizingMode.EXACTLY,
            last_available_height=100,
            last_computed_width=80,  # Computed fits in 200
            last_computed_height=100,
        )
        assert result is True
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

```python
# src/flow/layout/cache.py
"""Layout caching logic (matches Yoga's algorithm/Cache.cpp)."""

from __future__ import annotations

from flow.layout.intrinsic import SizingMode
from flow.layout.types import approx_equal


def can_use_cached_measurement(
    width_mode: SizingMode,
    available_width: float,
    height_mode: SizingMode,
    available_height: float,
    last_width_mode: SizingMode,
    last_available_width: float,
    last_height_mode: SizingMode,
    last_available_height: float,
    last_computed_width: float,
    last_computed_height: float,
) -> bool:
    """Check if cached measurement can be reused.

    Implements Yoga's cache validation logic:
    1. Exact match on sizing parameters
    2. StretchFit mode matches computed size
    3. FitContent can use MaxContent cache if still fits
    4. Stricter constraints reuse if content still valid

    Args:
        width_mode: Current width sizing mode
        available_width: Current available width
        height_mode: Current height sizing mode
        available_height: Current available height
        last_*: Previous measurement parameters
        last_computed_*: Previous computed dimensions

    Returns:
        True if cache can be reused, False if recalculation needed.
    """
    # Invalid cached values
    if last_computed_width < 0 or last_computed_height < 0:
        return False

    # Check width compatibility
    has_same_width = (
        last_width_mode == width_mode and
        approx_equal(last_available_width, available_width)
    )

    # Check height compatibility
    has_same_height = (
        last_height_mode == height_mode and
        approx_equal(last_available_height, available_height)
    )

    # Exact match
    if has_same_width and has_same_height:
        return True

    # StretchFit (EXACTLY) matches if computed equals available
    width_stretch_match = (
        width_mode == SizingMode.EXACTLY and
        approx_equal(available_width, last_computed_width)
    )

    height_stretch_match = (
        height_mode == SizingMode.EXACTLY and
        approx_equal(available_height, last_computed_height)
    )

    # FitContent can use MaxContent if still fits
    width_fit_content_valid = (
        width_mode == SizingMode.FIT_CONTENT and
        last_width_mode == SizingMode.MAX_CONTENT and
        (available_width >= last_computed_width or
         approx_equal(available_width, last_computed_width))
    )

    height_fit_content_valid = (
        height_mode == SizingMode.FIT_CONTENT and
        last_height_mode == SizingMode.MAX_CONTENT and
        (available_height >= last_computed_height or
         approx_equal(available_height, last_computed_height))
    )

    width_compatible = (
        has_same_width or width_stretch_match or width_fit_content_valid
    )
    height_compatible = (
        has_same_height or height_stretch_match or height_fit_content_valid
    )

    return width_compatible and height_compatible
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_cache.py -v
```

**Step 5: Commit**

```bash
git add src/flow/layout/cache.py tests/test_layout_cache.py
git commit -m "feat(layout): add can_use_cached_measurement for layout caching"
```

---

### Task 3.3: Integrate Caching in compute_layout

**Files:**
- Modify: `src/flow/layout/compute.py`
- Modify: `tests/test_layout_cache.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_layout_cache.py

class TestComputeLayoutCaching:
    def test_cache_hit_skips_calculation(self):
        """When cache is valid, layout calculation is skipped."""
        call_count = 0

        def counting_measure(available_width, available_height):
            nonlocal call_count
            call_count += 1
            return Size(80, 20)

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.auto(),
                height=Dimension.auto(),
            ),
            measure_func=counting_measure,
        )

        # First layout - should call measure
        compute_layout(node, Size(100, 100))
        assert call_count == 1

        # Second layout with same size - should use cache
        compute_layout(node, Size(100, 100))
        assert call_count == 1  # Still 1, cache was used

    def test_cache_miss_recalculates(self):
        """When available size changes, recalculate."""
        call_count = 0

        def counting_measure(available_width, available_height):
            nonlocal call_count
            call_count += 1
            return Size(80, 20)

        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.auto(),
                height=Dimension.auto(),
            ),
            measure_func=counting_measure,
        )

        compute_layout(node, Size(100, 100))
        assert call_count == 1

        # Different size - should recalculate
        compute_layout(node, Size(200, 200))
        assert call_count == 2
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

```python
# Modify compute_layout in src/flow/layout/compute.py

from flow.layout.cache import can_use_cached_measurement
from flow.layout.node import CachedMeasurement

def compute_layout(
    node: LayoutNode,
    available_space: Size,
    width_mode: SizingMode = SizingMode.EXACTLY,
    height_mode: SizingMode = SizingMode.EXACTLY,
) -> None:
    """Compute layout for a node and its children.

    Uses cached measurement when available and valid.
    """
    # Check cache first
    if node.cached_measurement is not None:
        cache = node.cached_measurement
        if can_use_cached_measurement(
            width_mode=width_mode,
            available_width=available_space.width,
            height_mode=height_mode,
            available_height=available_space.height,
            last_width_mode=cache.width_mode,
            last_available_width=cache.available_width,
            last_height_mode=cache.height_mode,
            last_available_height=cache.available_height,
            last_computed_width=cache.computed_width,
            last_computed_height=cache.computed_height,
        ):
            # Use cached result
            node.layout = LayoutResult(
                x=node.layout.x,
                y=node.layout.y,
                width=cache.computed_width,
                height=cache.computed_height,
            )
            return

    # ... existing layout calculation ...

    # After calculation, update cache
    node.cached_measurement = CachedMeasurement(
        available_width=available_space.width,
        available_height=available_space.height,
        width_mode=width_mode,
        height_mode=height_mode,
        computed_width=node.layout.width,
        computed_height=node.layout.height,
    )
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_layout_cache.py::TestComputeLayoutCaching -v
```

**Step 5: Commit**

```bash
git commit -am "feat(layout): integrate layout caching in compute_layout"
```

---

## Summary of All Tasks

| Phase | Task | Description | Files |
|-------|------|-------------|-------|
| 1 | 1.1 | Add AlignContent.SPACE_EVENLY | style.py |
| 1 | 1.2 | Implement SPACE_EVENLY in align_cross_axis | algorithm.py |
| 2 | 2.1 | Add BaselineFunc protocol | node.py |
| 2 | 2.2 | Implement calculate_baseline function | baseline.py |
| 2 | 2.3 | Integrate baseline in cross-axis alignment | compute.py |
| 3 | 3.1 | Add CachedMeasurement to LayoutNode | node.py |
| 3 | 3.2 | Implement can_use_cached_measurement | cache.py |
| 3 | 3.3 | Integrate caching in compute_layout | compute.py |

---

## Deferred Features (Not Recommended)

The following Yoga features are intentionally NOT included in this plan:

1. **Errata modes** - Backward compatibility with old Yoga versions. Flow is a new implementation with no legacy constraints.

2. **ExperimentalFeature.WebFlexBasis** - Experimental feature in Yoga for web compatibility. Not needed for our Python implementation.

3. **NodeType (Default/Text)** - We handle this via `MeasureFunc` already (Amendment Alpha).

---

## Verification

After implementing all tasks, run full test suite:

```bash
uv run pytest tests/test_layout*.py -v
```

Expected: All tests pass (233 existing + new tests ≈ 260 total)

---

## Dependencies

This plan builds on:
- `docs/plans/2025-12-02-yoga-layout.md` (fully implemented)
- `docs/plans/2025-12-02-yoga-parity-gaps.md` (fully implemented)

No external dependencies required.
