import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.tui.layout.algorithm import AvailableSpace
    from wtfui.tui.layout.types import Size


@dataclass(frozen=True)
class MeasureContext:
    renderer: str = "html"
    font_family: str = "sans-serif"
    font_weight: int = 400
    extra: dict[str, object] = field(default_factory=dict)


class MeasureFunc(Protocol):
    def __call__(
        self,
        available_width: AvailableSpace,
        available_height: AvailableSpace,
        context: MeasureContext,
    ) -> Size: ...


def create_text_measure(
    text: str,
    font_size: float = 16,
    chars_per_em: float = 0.5,
    line_height: float = 1.2,
) -> Callable[..., Size]:
    from wtfui.tui.layout.types import Size

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
                chars_per_line = max(1, int(max_width / char_width))
                num_lines = (len(text) + chars_per_line - 1) // chars_per_line
                return Size(
                    width=min(total_width, max_width),
                    height=num_lines * line_h,
                )

        return Size(width=total_width, height=line_h)

    return measure


_FONT_SIZE_PX_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*px")


def create_canvas_text_measure(text: str, font: str) -> Callable[..., Size]:
    import sys

    from wtfui.tui.layout.types import Size

    js = sys.modules.get("js")

    if js is None:
        return create_text_measure(text)

    try:
        document = getattr(js, "document", None)
        if document is None:
            return create_text_measure(text)

        canvas = document.createElement("canvas")
        ctx = canvas.getContext("2d")
        if ctx is None:
            return create_text_measure(text)

        ctx.font = font

        metrics = ctx.measureText(text)
        measured_width = float(metrics.width)

        font_size_match = _FONT_SIZE_PX_PATTERN.search(font)
        font_size = float(font_size_match.group(1)) if font_size_match else 16.0
        line_height = font_size * 1.2

    except Exception:
        return create_text_measure(text)

    def measure(
        available_width: AvailableSpace,
        available_height: AvailableSpace,
        context: MeasureContext,
    ) -> Size:
        total_width = measured_width

        if available_width.is_definite() and available_width.value is not None:
            max_width = available_width.value
            if total_width > max_width:
                chars = len(text)
                avg_char_width = (total_width * 1.1) / max(chars, 1)
                chars_per_line = max(1, int(max_width / avg_char_width))
                num_lines = (chars + chars_per_line - 1) // chars_per_line
                return Size(
                    width=min(total_width, max_width),
                    height=num_lines * line_height,
                )

        return Size(width=total_width, height=line_height)

    return measure


def create_pillow_text_measure(text: str, font_path: str, font_size: float) -> Callable[..., Size]:
    from wtfui.tui.layout.types import Size

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
        return create_text_measure(text, font_size=font_size)
