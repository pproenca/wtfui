"""ProgressBar Component for Console Demo.

A reusable progress bar that displays a percentage value as a text-based bar.
Supports both static floats and reactive Signal[float] values.

Usage:
    ProgressBar(value=75.0, color=Colors.Green._500)
    ProgressBar(value=state.cpu_percent, color="green")  # Reactive!
"""

from wtfui import Computed, Signal, component
from wtfui.core.style import Colors, Style
from wtfui.ui import HStack, Text

# Type alias for color specification
ColorSpec = str

# Map legacy color names to Colors enum values
_LEGACY_COLOR_MAP: dict[str, str] = {
    "green": Colors.Green._500,
    "cyan": Colors.Cyan._500,
    "red": Colors.Red._500,
    "yellow": Colors.Yellow._500,
    "blue": Colors.Blue._500,
}


def _resolve_color(color: ColorSpec) -> str:
    """Resolve color specification to a valid color string.

    Args:
        color: Either a Colors enum value or a legacy color name.

    Returns:
        Resolved color string for Style.
    """
    return _LEGACY_COLOR_MAP.get(color, color)


def _make_bar(value: float, width: int) -> str:
    """Generate bar string from percentage value."""
    filled = int((value / 100) * width)
    return "\u2588" * filled + "\u2591" * (width - filled)  # █ and ░


@component
def ProgressBar(value: float | Signal[float], color: ColorSpec = Colors.Green._500) -> None:
    """Render a text-based progress bar with reactive updates.

    Args:
        value: Percentage value (0-100), either static float or Signal[float].
        color: Color from Colors enum (recommended) or legacy color name.

    Examples:
        ProgressBar(value=75.0, color=Colors.Green._500)
        ProgressBar(value=state.cpu_percent, color="green")  # Reactive!
    """
    width = 20
    resolved_color = _resolve_color(color)

    # Normalize to reactive source (wrap static values in Signal)
    source = value if isinstance(value, Signal) else Signal(value)

    # Derived state - auto-updates when source changes
    percent_text = Computed(lambda: f"{source.value:.1f}% ")
    bar_text = Computed(lambda: _make_bar(source.value, width))

    # Layout props go directly on elements; Style handles visual styling only
    with HStack(height=1):
        Text(percent_text, style=Style(color=resolved_color, font_weight="bold"))
        Text(bar_text, style=Style(color=resolved_color))
