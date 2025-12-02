# src/flow/layout/measure.py
"""Text measurement protocol for intrinsic content sizing (Amendment Alpha).

This module provides the MeasureFunc protocol for measuring intrinsic content
sizes, particularly for text nodes. Different renderers can implement their
own measurement strategies:

- Server (HTML): Character count estimation (rough)
- Browser (Wasm): canvas.measureText() via JS Bridge
- Image: Pillow or freetype for exact pixel measurements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from flow.layout.algorithm import AvailableSpace
    from flow.layout.types import Size


@dataclass(frozen=True)
class MeasureContext:
    """Context passed to measure functions for renderer-specific hints."""

    renderer: str = "html"
    font_family: str = "sans-serif"
    font_weight: int = 400
    extra: dict[str, object] = field(default_factory=dict)


class MeasureFunc(Protocol):
    """Protocol for measuring intrinsic content size.

    A MeasureFunc is called during layout computation to determine the
    natural size of content (like text) that cannot be determined from
    style properties alone.
    """

    def __call__(
        self,
        available_width: AvailableSpace,
        available_height: AvailableSpace,
        context: MeasureContext,
    ) -> Size:
        """Measure content given available space constraints.

        Args:
            available_width: Available width constraint.
            available_height: Available height constraint.
            context: Renderer-specific hints and configuration.

        Returns:
            The intrinsic Size of the content.
        """
        ...


def create_text_measure(
    text: str,
    font_size: float = 16,
    chars_per_em: float = 0.5,
    line_height: float = 1.2,
) -> Callable[..., Size]:
    """Create a character-count based text measure function.

    This is a rough estimate for server-side rendering. For exact
    measurements, use renderer-specific implementations:
    - Browser: canvas.measureText() via JS Bridge
    - Image: Pillow ImageFont.getbbox() or freetype

    Args:
        text: The text content to measure.
        font_size: Font size in pixels.
        chars_per_em: Average character width as fraction of em.
        line_height: Line height multiplier.

    Returns:
        A MeasureFunc that estimates text dimensions.
    """
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


# Renderer-specific measure function factories (stubs for future implementation)


def create_canvas_text_measure(text: str, font: str) -> Callable[..., Size]:
    """Create a measure function that uses browser canvas.measureText().

    This will be called via the JS Bridge when running in WASM context.
    Implementation requires the RPC bridge to be set up.

    Args:
        text: The text content to measure.
        font: CSS font string (e.g., "16px sans-serif").

    Returns:
        A MeasureFunc (falls back to character estimation for now).
    """
    # Stub - actual implementation needs JS bridge
    return create_text_measure(text)


def create_pillow_text_measure(text: str, font_path: str, font_size: float) -> Callable[..., Size]:
    """Create a measure function using Pillow for exact pixel measurements.

    Args:
        text: The text content to measure.
        font_path: Path to the font file.
        font_size: Font size in pixels.

    Returns:
        A MeasureFunc using Pillow if available, else character estimation.
    """
    from flow.layout.types import Size

    try:
        from PIL import ImageFont  # type: ignore[import-untyped]

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
