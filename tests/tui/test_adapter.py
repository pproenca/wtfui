"""Test LayoutAdapter converts Elements to LayoutNodes."""

from wtfui.core.element import Element
from wtfui.tui.layout.style import FlexDirection


def test_adapter_import():
    """LayoutAdapter should be importable from wtfui.tui."""
    from wtfui.tui import LayoutAdapter

    assert LayoutAdapter is not None


def test_adapter_converts_simple_element():
    """LayoutAdapter should convert Element to LayoutNode."""
    from wtfui.tui import LayoutAdapter

    elem = Element(width=100, height=50)
    adapter = LayoutAdapter()
    node = adapter.to_layout_node(elem)

    assert node is not None
    assert node.style.width is not None


def test_adapter_converts_nested_elements():
    """LayoutAdapter should recursively convert children."""
    from wtfui.tui import LayoutAdapter

    parent = Element(flex_direction="column")
    child1 = Element(height=20)
    child2 = Element(height=30)
    parent.children.append(child1)
    parent.children.append(child2)

    adapter = LayoutAdapter()
    node = adapter.to_layout_node(parent)

    assert len(node.children) == 2
    assert node.style.flex_direction == FlexDirection.COLUMN
