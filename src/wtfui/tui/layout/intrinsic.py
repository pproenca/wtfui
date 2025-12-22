from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.layout.node import LayoutNode


def calculate_min_content_width(node: LayoutNode) -> float:
    style = node.style

    if style.width.is_defined() and not style.width.is_intrinsic():
        return style.width.value or 0

    if not node.children:
        return 0

    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        total = sum(calculate_min_content_width(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total
    else:
        return max((calculate_min_content_width(c) for c in node.children), default=0)


def calculate_max_content_width(node: LayoutNode) -> float:
    style = node.style

    if style.width.is_defined() and not style.width.is_intrinsic():
        return style.width.value or 0

    if not node.children:
        return 0

    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        total = sum(calculate_max_content_width(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total
    else:
        return max((calculate_max_content_width(c) for c in node.children), default=0)


def calculate_min_content_height(node: LayoutNode) -> float:
    style = node.style

    if style.height.is_defined() and not style.height.is_intrinsic():
        return style.height.value or 0

    if not node.children:
        return 0

    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        return max((calculate_min_content_height(c) for c in node.children), default=0)
    else:
        total = sum(calculate_min_content_height(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total


def calculate_max_content_height(node: LayoutNode) -> float:
    style = node.style

    if style.height.is_defined() and not style.height.is_intrinsic():
        return style.height.value or 0

    if not node.children:
        return 0

    is_row = style.flex_direction.is_row()
    gap = style.get_gap(style.flex_direction)

    if is_row:
        return max((calculate_max_content_height(c) for c in node.children), default=0)
    else:
        total = sum(calculate_max_content_height(c) for c in node.children)
        total += gap * max(0, len(node.children) - 1)
        return total


def calculate_fit_content_width(
    node: LayoutNode, available: float, max_clamp: float | None = None
) -> float:
    min_w = calculate_min_content_width(node)
    max_w = calculate_max_content_width(node)

    result = min(max_w, max(min_w, available))

    if max_clamp is not None:
        result = min(result, max_clamp)

    return result


def calculate_fit_content_height(
    node: LayoutNode, available: float, max_clamp: float | None = None
) -> float:
    min_h = calculate_min_content_height(node)
    max_h = calculate_max_content_height(node)

    result = min(max_h, max(min_h, available))

    if max_clamp is not None:
        result = min(result, max_clamp)

    return result
