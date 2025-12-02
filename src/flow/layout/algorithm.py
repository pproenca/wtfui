# src/flow/layout/algorithm.py
"""Flexbox algorithm types and functions for the Flow Layout Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
