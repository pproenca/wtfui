import sys
from typing import TYPE_CHECKING, Any

from wtfui.core.protocol import Renderer, RenderNode
from wtfui.tui.layout.types import parse_css_dimension
from wtfui.tui.renderer.buffer import Buffer
from wtfui.tui.renderer.cell import Cell
from wtfui.tui.renderer.diff import diff_buffers
from wtfui.tui.renderer.theme import apply_cls_to_cell

if TYPE_CHECKING:
    from wtfui.core.element import Element
    from wtfui.core.style import Style


class ConsoleRenderer(Renderer):
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.front_buffer = Buffer(width, height)
        self.back_buffer = Buffer(width, height)

        self.mouse_x: int = -1
        self.mouse_y: int = -1

        self.last_rendered_height: int = 0
        self.last_cursor_y: int = 0
        self._cached_frame: str | None = None

        self.cursor_target: tuple[int, int] | None = None

    def update_mouse(self, x: int, y: int) -> bool:
        if self.mouse_x == x and self.mouse_y == y:
            return False

        self.mouse_x = x
        self.mouse_y = y
        return True

    def render(self, element: Element) -> str:
        from wtfui.tui.builder import RenderTreeBuilder

        self.clear()
        node = RenderTreeBuilder().build(element)
        self.render_node(node)
        return self.flush()

    def render_node(self, node: RenderNode, x: int = 0, y: int = 0) -> Any:
        cls = node.props.get("cls", "")

        if node.text_content:
            self.render_text_at(x, y, node.text_content, cls=cls)
            return None

        if node.label:
            self.render_text_at(x, y, node.label, cls=cls)
            return None

        for child in node.children:
            self.render_node(child, x, y)

        return None

    def render_node_with_layout(
        self,
        node: RenderNode,
        parent_x: int = 0,
        parent_y: int = 0,
    ) -> None:
        if node.layout is not None:
            left = int(node.layout.x)
            top = int(node.layout.y)
            width = int(node.layout.width)
            height = max(1, int(node.layout.height))
        else:
            style_dict = node.props.get("style", {})
            left = parse_css_dimension(style_dict.get("left", 0))
            top = parse_css_dimension(style_dict.get("top", 0))
            width = parse_css_dimension(style_dict.get("width", 0))
            height = parse_css_dimension(style_dict.get("height", 1))

        style_dict = node.props.get("style") or {}

        abs_x = parent_x + left
        abs_y = parent_y + top

        fuse_style: Style | None = style_dict.get("_wtfui_style") if style_dict else None

        if fuse_style and fuse_style.hover:
            is_hovered = (
                self.mouse_x >= abs_x
                and self.mouse_x < abs_x + (width or 1)
                and self.mouse_y >= abs_y
                and self.mouse_y < abs_y + (height or 1)
            )
            if is_hovered:
                fuse_style = fuse_style | fuse_style.hover

        cls = node.props.get("cls", "")

        if node.text_content:
            self._render_text_with_style(
                abs_x, abs_y, node.text_content, cls=cls, fuse_style=fuse_style, max_width=width
            )
        elif node.label:
            self._render_text_with_style(
                abs_x, abs_y, node.label, cls=cls, fuse_style=fuse_style, max_width=width
            )

        for child in node.children:
            self.render_node_with_layout(child, abs_x, abs_y)

    def _render_text_with_style(
        self,
        x: int,
        y: int,
        text: str,
        cls: str = "",
        fuse_style: Style | None = None,
        fg: tuple[int, int, int] | None = None,
        bg: tuple[int, int, int] | None = None,
        max_width: int = 0,
    ) -> None:
        from wtfui.tui.renderer.theme import apply_style_to_cell

        max_width = max(0, max_width)
        if max_width > 0:
            text = text[:max_width]

        for i, char in enumerate(text):
            cell = Cell(char=char, fg=fg, bg=bg)

            if cls:
                apply_cls_to_cell(cell, cls)

            if fuse_style:
                apply_style_to_cell(cell, fuse_style)

            self.back_buffer.set(x + i, y, cell)

    def render_text(self, content: str) -> Any:
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
        for i, char in enumerate(text):
            cell = Cell(char=char, fg=fg, bg=bg)
            if cls:
                apply_cls_to_cell(cell, cls)
            self.back_buffer.set(x + i, y, cell)

    def flush(self, inline: bool = False) -> str:
        self._cached_frame = None

        result = diff_buffers(self.front_buffer, self.back_buffer)

        parts: list[str] = []

        if inline and self.last_rendered_height > 0:
            parts.append(f"\x1b[{self.last_rendered_height}A")

            parts.append("\r")

        parts.append(result.ansi_output)

        self.last_rendered_height = self.height

        if self.cursor_target:
            self.last_cursor_y = self.cursor_target[1]
        else:
            self.last_cursor_y = self.height - 1

        self.front_buffer, self.back_buffer = self.back_buffer, self.front_buffer

        return "".join(parts)

    def get_clear_sequence(self) -> str:
        if self.last_rendered_height == 0:
            return ""

        if self.last_cursor_y > 0:
            return f"\x1b[{self.last_cursor_y}A\x1b[J"
        else:
            return "\x1b[J"

    def repaint(self) -> str:
        if self.last_rendered_height == 0:
            return ""

        if self._cached_frame is None:
            self._cached_frame = self._compute_full_frame()

        return self._cached_frame

    def _compute_full_frame(self) -> str:
        from wtfui.tui.renderer import ansi
        from wtfui.tui.renderer.diff import _build_style_sequence

        parts: list[str] = []

        last_fg: tuple[int, int, int] | None = None
        last_bg: tuple[int, int, int] | None = None
        last_bold: bool = False
        last_dim: bool = False
        last_italic: bool = False
        last_underline: bool = False

        for y in range(self.height):
            parts.append(ansi.cursor_move(0, y))
            for x in range(self.width):
                cell = self.front_buffer.get(x, y)

                style_seq = _build_style_sequence(
                    cell, last_fg, last_bg, last_bold, last_dim, last_italic, last_underline
                )
                if style_seq:
                    parts.append(style_seq)
                    last_fg = cell.fg
                    last_bg = cell.bg
                    last_bold = cell.bold
                    last_dim = cell.dim
                    last_italic = cell.italic
                    last_underline = cell.underline

                parts.append(cell.char)

        parts.append(ansi.reset_style())

        if self.cursor_target:
            cx, cy = self.cursor_target
            parts.append(ansi.cursor_move(cx, cy))
            parts.append(ansi.cursor_show())
        else:
            parts.append(ansi.cursor_move(0, self.height - 1))

        return "".join(parts)

    def clear(self) -> None:
        self.back_buffer.clear()

    def write_to_stdout(self, output: str) -> None:
        sys.stdout.write(output)
        sys.stdout.flush()

    def resize(self, width: int, height: int, clear: bool = True) -> str:
        from wtfui.tui.renderer import ansi

        self.width = width
        self.height = height
        self.front_buffer = Buffer(width, height)
        self.back_buffer = Buffer(width, height)

        if clear:
            return ansi.clear_screen()
        return ""
