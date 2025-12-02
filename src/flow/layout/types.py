# src/flow/layout/types.py
"""Core types for the Flow Layout Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DimensionUnit(Enum):
    """Unit type for dimension values."""

    AUTO = "auto"
    POINTS = "px"
    PERCENT = "%"
    MIN_CONTENT = "min-content"
    MAX_CONTENT = "max-content"
    FIT_CONTENT = "fit-content"


@dataclass(frozen=True, slots=True)
class Dimension:
    """A dimension value that can be auto, points, or percentage."""

    value: float | None = None
    _unit: DimensionUnit = DimensionUnit.AUTO

    @classmethod
    def auto(cls) -> Dimension:
        """Create an auto dimension."""
        return cls(None, DimensionUnit.AUTO)

    @classmethod
    def points(cls, value: float) -> Dimension:
        """Create a dimension in points (pixels)."""
        return cls(value, DimensionUnit.POINTS)

    @classmethod
    def percent(cls, value: float) -> Dimension:
        """Create a percentage dimension."""
        return cls(value, DimensionUnit.PERCENT)

    @classmethod
    def min_content(cls) -> Dimension:
        """Create a min-content intrinsic dimension."""
        return cls(None, DimensionUnit.MIN_CONTENT)

    @classmethod
    def max_content(cls) -> Dimension:
        """Create a max-content intrinsic dimension."""
        return cls(None, DimensionUnit.MAX_CONTENT)

    @classmethod
    def fit_content(cls, max_size: float | None = None) -> Dimension:
        """Create a fit-content intrinsic dimension with optional clamp."""
        return cls(max_size, DimensionUnit.FIT_CONTENT)

    @property
    def unit(self) -> str:
        """Return the unit as a string for compatibility."""
        return self._unit.value

    def is_auto(self) -> bool:
        """Check if this is an auto dimension."""
        return self._unit == DimensionUnit.AUTO

    def is_intrinsic(self) -> bool:
        """Check if this is an intrinsic size (min/max/fit-content)."""
        return self._unit in (
            DimensionUnit.MIN_CONTENT,
            DimensionUnit.MAX_CONTENT,
            DimensionUnit.FIT_CONTENT,
        )

    def is_defined(self) -> bool:
        """Check if this dimension has a defined value."""
        return self._unit != DimensionUnit.AUTO and self.value is not None

    def resolve(self, parent_value: float) -> float | None:
        """Resolve this dimension to a concrete value.

        Args:
            parent_value: The parent's dimension for percentage calculations.

        Returns:
            The resolved value in points, or None if auto.
        """
        if self._unit == DimensionUnit.POINTS:
            return self.value
        elif self._unit == DimensionUnit.PERCENT and self.value is not None:
            return (self.value / 100) * parent_value
        return None


@dataclass(frozen=True, slots=True)
class Size:
    """A 2D size with width and height."""

    width: float = 0
    height: float = 0

    @classmethod
    def zero(cls) -> Size:
        """Create a zero-sized Size."""
        return cls(0, 0)


@dataclass(frozen=True, slots=True)
class Point:
    """A 2D point with x and y coordinates."""

    x: float = 0
    y: float = 0


@dataclass(frozen=True, slots=True)
class Rect:
    """A rectangle with position and size."""

    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def left(self) -> float:
        """Left edge x-coordinate."""
        return self.x

    @property
    def top(self) -> float:
        """Top edge y-coordinate."""
        return self.y

    @property
    def right(self) -> float:
        """Right edge x-coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Bottom edge y-coordinate."""
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Edges:
    """Edge values for margin, padding, or border."""

    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> Edges:
        """Create edges with equal values on all sides."""
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, horizontal: float = 0, vertical: float = 0) -> Edges:
        """Create edges with symmetric horizontal and vertical values."""
        return cls(vertical, horizontal, vertical, horizontal)

    @classmethod
    def zero(cls) -> Edges:
        """Create zero edges."""
        return cls(0, 0, 0, 0)

    @property
    def horizontal(self) -> float:
        """Sum of left and right edges."""
        return self.left + self.right

    @property
    def vertical(self) -> float:
        """Sum of top and bottom edges."""
        return self.top + self.bottom


@dataclass(frozen=True, slots=True)
class Spacing:
    """Spacing with dimension values for each edge."""

    top: Dimension | None = None
    right: Dimension | None = None
    bottom: Dimension | None = None
    left: Dimension | None = None

    def __post_init__(self) -> None:
        """Set default auto dimensions for None values."""
        # Use object.__setattr__ since this is a frozen dataclass
        if self.top is None:
            object.__setattr__(self, "top", Dimension.auto())
        if self.right is None:
            object.__setattr__(self, "right", Dimension.auto())
        if self.bottom is None:
            object.__setattr__(self, "bottom", Dimension.auto())
        if self.left is None:
            object.__setattr__(self, "left", Dimension.auto())

    @classmethod
    def all(cls, value: Dimension) -> Spacing:
        """Create spacing with equal values on all sides."""
        return cls(value, value, value, value)

    @classmethod
    def zero(cls) -> Spacing:
        """Create zero spacing."""
        zero = Dimension.points(0)
        return cls(zero, zero, zero, zero)

    def resolve(self, width: float, height: float) -> Edges:
        """Resolve spacing dimensions to concrete edge values.

        Args:
            width: Parent width for horizontal percentage calculations.
            height: Parent height for vertical percentage calculations.

        Returns:
            Resolved Edges with concrete values. Auto resolves to 0.
        """
        return Edges(
            top=self.top.resolve(height) or 0 if self.top else 0,
            right=self.right.resolve(width) or 0 if self.right else 0,
            bottom=self.bottom.resolve(height) or 0 if self.bottom else 0,
            left=self.left.resolve(width) or 0 if self.left else 0,
        )


# Council Directive: Floating-Point Precision
LAYOUT_EPSILON = 0.001


def approx_equal(a: float, b: float, epsilon: float = LAYOUT_EPSILON) -> bool:
    """Check if two floats are approximately equal within epsilon.

    This prevents infinite oscillation in flex basis calculations
    due to floating-point errors like 0.30000000004.
    """
    return abs(a - b) < epsilon


def snap_to_pixel(value: float, scale: float = 1.0) -> float:
    """Snap a layout value to the nearest sub-pixel grid.

    This prevents CSS rendering inconsistencies between browsers
    that floor/ceil sub-pixels differently.

    Args:
        value: The value to snap.
        scale: The pixel scale (2 = half-pixel grid, etc).

    Returns:
        The snapped value.
    """
    return round(value * scale) / scale
