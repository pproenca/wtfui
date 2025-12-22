from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.layout.node import LayoutNode


def calculate_baseline(node: LayoutNode) -> float:
    from wtfui.tui.layout.style import AlignItems, Position

    if node.has_baseline_func() and node.baseline_func is not None:
        result = node.baseline_func(node.layout.width, node.layout.height)
        return result if result is not None else node.layout.height

    baseline_child: LayoutNode | None = None

    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            continue

        effective_align = child.style.align_self or node.style.align_items
        if effective_align == AlignItems.BASELINE:
            baseline_child = child
            break

        if baseline_child is None:
            baseline_child = child

    if baseline_child is None:
        return node.layout.height

    child_baseline = calculate_baseline(baseline_child)
    return child_baseline + baseline_child.layout.y


def is_baseline_layout(node: LayoutNode) -> bool:
    from wtfui.tui.layout.style import AlignItems, Position

    if node.style.flex_direction.is_column():
        return False

    if node.style.align_items == AlignItems.BASELINE:
        return True

    for child in node.children:
        if child.style.position == Position.ABSOLUTE:
            continue
        if child.style.align_self == AlignItems.BASELINE:
            return True

    return False
