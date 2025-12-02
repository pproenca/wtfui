# src/flow/layout/algorithm.py
"""Flexbox algorithm types and functions for the Flow Layout Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.style import AlignItems, FlexDirection, JustifyContent


class SizingMode(Enum):
    """Box sizing mode for layout calculations."""

    CONTENT_BOX = "content-box"
    BORDER_BOX = "border-box"

    def is_content_box(self) -> bool:
        """Check if using content-box sizing (excludes padding/border)."""
        return self == SizingMode.CONTENT_BOX

    def is_border_box(self) -> bool:
        """Check if using border-box sizing (includes padding/border)."""
        return self == SizingMode.BORDER_BOX


@dataclass(frozen=True)
class AvailableSpace:
    """Represents available space for layout computation.

    CSS defines three sizing modes:
    - definite: A specific pixel value is available
    - min-content: Shrink as small as possible without overflow
    - max-content: Expand to fit content without wrapping
    """

    _value: float | None
    _mode: str  # "definite", "min-content", "max-content"

    @classmethod
    def definite(cls, value: float) -> AvailableSpace:
        """Create a definite (concrete pixel value) available space."""
        return cls(value, "definite")

    @classmethod
    def min_content(cls) -> AvailableSpace:
        """Create a min-content available space.

        Min-content means the smallest size without overflow.
        """
        return cls(None, "min-content")

    @classmethod
    def max_content(cls) -> AvailableSpace:
        """Create a max-content available space.

        Max-content means the ideal size to fit all content.
        """
        return cls(None, "max-content")

    def is_definite(self) -> bool:
        """Check if this is a definite (concrete) space."""
        return self._mode == "definite"

    def is_min_content(self) -> bool:
        """Check if this is min-content sizing."""
        return self._mode == "min-content"

    def is_max_content(self) -> bool:
        """Check if this is max-content sizing."""
        return self._mode == "max-content"

    @property
    def value(self) -> float | None:
        """Get the concrete value (if definite) or None."""
        return self._value

    def resolve(self) -> float:
        """Resolve to a concrete value.

        Returns:
            The definite value, 0 for min-content, or infinity for max-content.
        """
        if self._value is not None:
            return self._value
        return 0.0 if self.is_min_content() else float("inf")


def resolve_flexible_lengths(
    items: list[LayoutNode],
    container_main_size: float,
    direction: FlexDirection,
    gap: float,
) -> list[float]:
    """Resolve flex item sizes based on flex-grow/flex-shrink.

    Implements CSS Flexbox spec section 9.7:
    https://www.w3.org/TR/css-flexbox-1/#resolve-flexible-lengths

    Args:
        items: List of LayoutNodes to size.
        container_main_size: Available space in the main axis.
        direction: Flex direction (row or column).
        gap: Gap between items.

    Returns:
        List of resolved main-axis sizes for each item.
    """
    if not items:
        return []

    # Calculate total gap space
    total_gap = gap * (len(items) - 1) if len(items) > 1 else 0
    available_space = container_main_size - total_gap

    # Get flex basis for each item
    bases: list[float] = []
    for item in items:
        basis = item.style.flex_basis
        if basis.is_defined():
            bases.append(basis.resolve(container_main_size) or 0)
        else:
            # Auto basis - use width/height based on direction
            dim = item.style.width if direction.is_row() else item.style.height
            bases.append(dim.resolve(container_main_size) or 0)

    total_basis = sum(bases)
    free_space = available_space - total_basis

    # Calculate flex factors
    if free_space >= 0:
        # Growing: distribute free space according to flex-grow
        total_grow = sum(item.style.flex_grow for item in items)
        if total_grow == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_grow / total_grow))
            for base, item in zip(bases, items, strict=False)
        ]
    else:
        # Shrinking: reduce sizes according to flex-shrink weighted by basis
        total_shrink = sum(
            item.style.flex_shrink * base for base, item in zip(bases, items, strict=False)
        )
        if total_shrink == 0:
            return bases

        return [
            base + (free_space * (item.style.flex_shrink * base / total_shrink))
            for base, item in zip(bases, items, strict=False)
        ]


def distribute_justify_content(
    item_sizes: list[float],
    container_size: float,
    justify: JustifyContent,
    gap: float,
) -> list[float]:
    """Calculate item positions along main axis based on justify-content.

    Implements CSS Flexbox spec section 9.5 (Main-Axis Alignment):
    https://www.w3.org/TR/css-flexbox-1/#algo-main-align

    Args:
        item_sizes: List of item sizes in the main axis.
        container_size: Total container size in the main axis.
        justify: JustifyContent value.
        gap: Gap between items.

    Returns:
        List of positions for each item.
    """
    from flow.layout.style import JustifyContent

    if not item_sizes:
        return []

    n = len(item_sizes)
    total_item_size = sum(item_sizes)
    total_gap = gap * (n - 1) if n > 1 else 0
    free_space = container_size - total_item_size - total_gap

    positions: list[float] = []

    if justify == JustifyContent.FLEX_START:
        pos = 0.0
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.FLEX_END:
        pos = free_space
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.CENTER:
        pos = free_space / 2
        for size in item_sizes:
            positions.append(pos)
            pos += size + gap

    elif justify == JustifyContent.SPACE_BETWEEN:
        if n == 1:
            positions.append(0.0)
        else:
            spacing = free_space / (n - 1)
            pos = 0.0
            for size in item_sizes:
                positions.append(pos)
                pos += size + spacing

    elif justify == JustifyContent.SPACE_AROUND:
        spacing = free_space / n
        pos = spacing / 2
        for size in item_sizes:
            positions.append(pos)
            pos += size + spacing

    elif justify == JustifyContent.SPACE_EVENLY:
        spacing = free_space / (n + 1)
        pos = spacing
        for size in item_sizes:
            positions.append(pos)
            pos += size + spacing

    return positions


def align_cross_axis(
    item_sizes: list[float],
    container_cross: float,
    align: AlignItems,
) -> list[tuple[float, float]]:
    """Calculate cross-axis position and size for each item.

    Implements CSS Flexbox spec section 9.6 (Cross-Axis Alignment):
    https://www.w3.org/TR/css-flexbox-1/#algo-cross-align

    Args:
        item_sizes: List of item sizes in the cross axis.
        container_cross: Total container size in the cross axis.
        align: AlignItems value.

    Returns:
        List of (position, size) tuples for each item.
    """
    from flow.layout.style import AlignItems

    if not item_sizes:
        return []

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


def apply_auto_margins(
    items: list[LayoutNode],
    positions: list[float],
    sizes: list[float],
    container_size: float,
    is_row: bool,
) -> list[float]:
    """Apply auto margins to adjust item positions.

    Auto margins absorb free space and override justify-content for the affected item.
    This only applies when there is a single item in the line, or when items have
    explicit auto margins that should override the default justify-content behavior.

    Implements CSS Flexbox spec section 8.1 (Aligning with auto margins):
    https://www.w3.org/TR/css-flexbox-1/#auto-margins

    Args:
        items: List of LayoutNodes.
        positions: List of item positions (from justify-content).
        sizes: List of item sizes in the main axis.
        container_size: Total container size in the main axis.
        is_row: True for row direction, False for column.

    Returns:
        List of adjusted positions with auto margins applied.
    """
    if not items:
        return positions

    adjusted = list(positions)

    # Check if there's only one item - in this case, auto margins work as expected
    if len(items) == 1:
        margin = items[0].style.margin
        size = sizes[0]

        # Only apply auto margins if they're explicitly set for alignment
        # Skip if all margins are auto (which is the default state)
        all_auto = (
            margin.left_is_auto()
            and margin.right_is_auto()
            and margin.top_is_auto()
            and margin.bottom_is_auto()
        )

        if all_auto:
            # Default state - don't apply auto margin logic
            return adjusted

        # Auto margins only make sense when there's free space
        has_free_space = container_size > size

        if is_row and has_free_space:
            left_auto = margin.left_is_auto()
            right_auto = margin.right_is_auto()

            # Only apply if explicitly using auto margins for alignment
            # (both auto = centering, or left auto = right align)
            if left_auto and right_auto:
                # Both auto: center the item
                remaining = container_size - size
                adjusted[0] = remaining / 2
            elif left_auto and not right_auto:
                # Left auto only (with explicit right=0): push item to the right
                adjusted[0] = container_size - size
            # right_auto alone doesn't change position (stays at left)
        elif not is_row and has_free_space:
            top_auto = margin.top_is_auto()
            bottom_auto = margin.bottom_is_auto()

            if top_auto and bottom_auto:
                # Both auto: center the item
                remaining = container_size - size
                adjusted[0] = remaining / 2
            elif top_auto and not bottom_auto:
                # Top auto only (with explicit bottom=0): push item to the bottom
                adjusted[0] = container_size - size
            # bottom_auto alone doesn't change position (stays at top)

    # For multiple items: auto margins don't override justify-content positioning
    # The free space distribution has already been handled by justify-content

    return adjusted
