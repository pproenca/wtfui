# src/flow/ui/spinner.py
"""Spinner - Animated loading indicator for terminal UI."""

from __future__ import annotations

from flow.element import Element
from flow.renderer.protocol import RenderNode

# Common spinner frame sets
BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
DOT_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
LINE_FRAMES = ["-", "\\", "|", "/"]
ARROW_FRAMES = ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"]


class Spinner(Element):
    """Animated spinner component.

    The spinner cycles through animation frames, typically
    rendered at ~12 FPS (80ms per frame) for smooth animation.

    Usage with Signal/Effect for animation:
        spinner = Spinner()

        async def animate():
            while True:
                spinner.advance()
                await asyncio.sleep(0.08)

        Effect(animate)
    """

    def __init__(
        self,
        frames: list[str] | None = None,
        cls: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize spinner.

        Args:
            frames: Animation frames (defaults to braille).
            cls: CSS class string for styling.
            **kwargs: Additional props.
        """
        super().__init__(cls=cls, **kwargs)
        self.frames = frames if frames is not None else BRAILLE_FRAMES
        self._frame_idx = 0
        self.cls = cls

    @property
    def current_frame(self) -> str:
        """Get the current animation frame."""
        return self.frames[self._frame_idx]

    def advance(self) -> None:
        """Advance to next frame (wraps at end)."""
        self._frame_idx = (self._frame_idx + 1) % len(self.frames)

    def reset(self) -> None:
        """Reset to first frame."""
        self._frame_idx = 0

    def to_render_node(self) -> RenderNode:
        """Convert to RenderNode for rendering."""
        return RenderNode(
            tag="Spinner",
            element_id=id(self),
            props={"cls": self.cls},
            text_content=self.current_frame,
        )
