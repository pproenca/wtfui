# tests/test_layout_node.py
from flow.layout.node import LayoutNode, LayoutResult
from flow.layout.style import FlexDirection, FlexStyle
from flow.layout.types import Dimension


class TestLayoutNode:
    def test_create_node(self):
        node = LayoutNode(style=FlexStyle())
        assert node.style.flex_direction.is_row()
        assert len(node.children) == 0

    def test_add_children(self):
        parent = LayoutNode(style=FlexStyle())
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=2.0))

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1.parent is parent
        assert child2.parent is parent

    def test_remove_child(self):
        parent = LayoutNode(style=FlexStyle())
        child = LayoutNode(style=FlexStyle())

        parent.add_child(child)
        assert len(parent.children) == 1

        parent.remove_child(child)
        assert len(parent.children) == 0
        assert child.parent is None

    def test_dirty_flag(self):
        node = LayoutNode(style=FlexStyle())
        assert node.is_dirty()

        node.clear_dirty()
        assert not node.is_dirty()

        node.mark_dirty()
        assert node.is_dirty()

    def test_dirty_propagates_to_parent(self):
        parent = LayoutNode(style=FlexStyle())
        child = LayoutNode(style=FlexStyle())
        parent.add_child(child)

        parent.clear_dirty()
        child.clear_dirty()
        assert not parent.is_dirty()

        child.mark_dirty()
        assert parent.is_dirty()


class TestLayoutResult:
    def test_layout_result(self):
        result = LayoutResult(x=10, y=20, width=100, height=50)
        assert result.x == 10
        assert result.y == 20
        assert result.width == 100
        assert result.height == 50

    def test_layout_result_edges(self):
        result = LayoutResult(x=10, y=20, width=100, height=50)
        assert result.left == 10
        assert result.top == 20
        assert result.right == 110
        assert result.bottom == 70


class TestLayoutNodeTree:
    def test_tree_structure(self):
        root = LayoutNode(style=FlexStyle(width=Dimension.points(300)))
        row = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
        cell1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        cell2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(row)
        row.add_child(cell1)
        row.add_child(cell2)

        assert root.children[0] is row
        assert row.children[0] is cell1
        assert row.children[1] is cell2
