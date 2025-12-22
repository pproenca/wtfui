from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.core.protocol import RenderNode
    from wtfui.tui.layout.node import LayoutNode


class SemanticLocator:
    def __init__(
        self,
        render_tree: RenderNode,
        element_to_layout: dict[int, LayoutNode],
    ) -> None:
        self._render_tree = render_tree
        self._element_to_layout = element_to_layout

    def find_by_text(
        self,
        text: str,
        partial: bool = False,
    ) -> RenderNode | None:
        return self._find_text_recursive(self._render_tree, text, partial)

    def _find_text_recursive(
        self,
        node: RenderNode,
        text: str,
        partial: bool,
    ) -> RenderNode | None:
        if node.text_content and (
            (partial and text in node.text_content) or (not partial and text == node.text_content)
        ):
            return node

        if node.label and (
            (partial and text in node.label) or (not partial and text == node.label)
        ):
            return node

        for child in node.children:
            found = self._find_text_recursive(child, text, partial)
            if found is not None:
                return found

        return None

    def get_absolute_bounds(self, node: RenderNode) -> tuple[float, float, float, float]:
        layout = self._element_to_layout[node.element_id]

        abs_x = layout.layout.x
        abs_y = layout.layout.y
        width = layout.layout.width
        height = layout.layout.height

        curr = layout.parent
        while curr is not None:
            abs_x += curr.layout.x
            abs_y += curr.layout.y
            curr = curr.parent

        return (abs_x, abs_y, width, height)

    def get_center(self, node: RenderNode) -> tuple[float, float]:
        x, y, w, h = self.get_absolute_bounds(node)
        return (x + w / 2, y + h / 2)
