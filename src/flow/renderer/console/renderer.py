# src/flow/renderer/console/renderer.py
"""ConsoleRenderer - Terminal-based renderer with double buffering."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from flow.renderer.console.buffer import Buffer
from flow.renderer.console.cell import Cell
from flow.renderer.console.diff import diff_buffers
from flow.renderer.console.theme import apply_cls_to_cell
from flow.renderer.protocol import Renderer, RenderNode

if TYPE_CHECKING:
    from flow.element import Element


class ConsoleRenderer(Renderer):
    """Terminal renderer using double-buffered differential painting.

    Maintains two buffers:
    - front_buffer: What is currently displayed on screen
    - back_buffer: What the next frame will look like

    flush() computes the diff and emits minimal ANSI sequences.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize renderer with terminal dimensions.

        Args:
            width: Terminal width in columns.
            height: Terminal height in rows.
        """
        self.width = width
        self.height = height
        self.front_buffer = Buffer(width, height)
        self.back_buffer = Buffer(width, height)

    def render(self, element: Element) -> str:
        """Render an element tree to ANSI string.

        Note: This is a convenience method. For animations,
        use render_node + flush for differential updates.
        """
        self.clear()
        node = element.to_render_node()
        self.render_node(node)
        return self.flush()

    def render_node(self, node: RenderNode, x: int = 0, y: int = 0) -> Any:
        """Render a RenderNode to the back buffer.

        Args:
            node: The RenderNode to render.
            x: X offset for positioning.
            y: Y offset for positioning.
        """
        # Get style from cls prop
        cls = node.props.get("cls", "")

        # Handle text content
        if node.text_content:
            self.render_text_at(x, y, node.text_content, cls=cls)
            return None

        if node.label:
            self.render_text_at(x, y, node.label, cls=cls)
            return None

        # Render children at same position (layout should offset)
        for child in node.children:
            self.render_node(child, x, y)

        return None

    def render_node_with_layout(
        self,
        node: RenderNode,
        parent_x: int = 0,
        parent_y: int = 0,
    ) -> None:
        """Render a RenderNode using layout position from style.

        Expects node.props["style"] to contain layout coordinates.

        Args:
            node: The RenderNode with layout style.
            parent_x: Parent's absolute x position.
            parent_y: Parent's absolute y position.
        """
        style = node.props.get("style", {})

        # Get position from layout (already computed by Yoga)
        # Style contains "top", "left" from layout computation
        left = int(style.get("left", "0").replace("px", ""))
        top = int(style.get("top", "0").replace("px", ""))

        abs_x = parent_x + left
        abs_y = parent_y + top

        cls = node.props.get("cls", "")

        # Handle text content
        if node.text_content:
            self.render_text_at(abs_x, abs_y, node.text_content, cls=cls)
        elif node.label:
            self.render_text_at(abs_x, abs_y, node.label, cls=cls)

        # Render children
        for child in node.children:
            self.render_node_with_layout(child, abs_x, abs_y)

    def render_text(self, content: str) -> Any:
        """Render text content (protocol compliance)."""
        return content

    def render_text_at(
        self,
        x: int,
        y: int,
        text: str,
        cls: str = "",
        fg: tuple[int, int, int] | None = None,
        bg: tuple[int, int, int] | None = None,
    ) -> None:
        """Write text to back buffer at position.

        Args:
            x: Column position.
            y: Row position.
            text: Text to write.
            cls: Tailwind-style classes.
            fg: Override foreground color.
            bg: Override background color.
        """
        for i, char in enumerate(text):
            cell = Cell(char=char, fg=fg, bg=bg)
            if cls:
                apply_cls_to_cell(cell, cls)
            self.back_buffer.set(x + i, y, cell)

    def flush(self) -> str:
        """Compute diff and generate ANSI output.

        After flush, front buffer is updated to match back buffer.

        Returns:
            ANSI escape sequence string to update terminal.
        """
        result = diff_buffers(self.front_buffer, self.back_buffer)

        # Swap buffers (back becomes front for next frame)
        self.front_buffer = self.back_buffer.clone()

        return result.ansi_output

    def clear(self) -> None:
        """Clear the back buffer."""
        self.back_buffer.clear()

    def write_to_stdout(self, output: str) -> None:
        """Write ANSI output to stdout."""
        sys.stdout.write(output)
        sys.stdout.flush()

    def resize(self, width: int, height: int) -> None:
        """Handle terminal resize.

        Args:
            width: New width.
            height: New height.
        """
        self.width = width
        self.height = height
        self.front_buffer = Buffer(width, height)
        self.back_buffer = Buffer(width, height)
