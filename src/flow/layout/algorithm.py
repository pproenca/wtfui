# src/flow/layout/algorithm.py
"""Flexbox algorithm types and functions for the Flow Layout Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexDirection, JustifyContent


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
