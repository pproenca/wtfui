# tests/test_layout_node.py
from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import FlexDirection, FlexStyle
from wtfui.tui.layout.types import Dimension


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


class TestMarkDirtyInvalidatesCache:
    def test_mark_dirty_invalidates_measurement_cache(self):
        """mark_dirty should also invalidate cached measurements."""
        from wtfui.tui.layout.node import CachedMeasurement, MeasureMode

        node = LayoutNode(style=FlexStyle())
        # Clear initial dirty flag (simulates after layout computation)
        node.clear_dirty()

        # Simulate cached measurement (would be set during layout computation)
        node.cached_measurement = CachedMeasurement(
            available_width=100,
            available_height=100,
            width_mode=MeasureMode.EXACTLY,
            height_mode=MeasureMode.EXACTLY,
            computed_width=50,
            computed_height=20,
        )

        node.mark_dirty()

        assert node.cached_measurement is None, "mark_dirty should clear measurement cache"


class TestLayoutNodeCycleDetection:
    def test_layout_node_rejects_self_as_child(self):
        """A node cannot be its own child."""
        import pytest

        node = LayoutNode(style=FlexStyle())

        with pytest.raises(ValueError, match=r"[Cc]ircular"):
            node.add_child(node)

    def test_layout_node_rejects_circular_parent(self):
        """Adding a node as its own ancestor should raise ValueError."""
        import pytest

        node_a = LayoutNode(style=FlexStyle())
        node_b = LayoutNode(style=FlexStyle())

        node_a.add_child(node_b)

        with pytest.raises(ValueError, match=r"[Cc]ircular"):
            node_b.add_child(node_a)

    def test_layout_node_rejects_deep_circular_reference(self):
        """Cycle detection should work for deeper ancestor chains."""
        import pytest

        node_a = LayoutNode(style=FlexStyle())
        node_b = LayoutNode(style=FlexStyle())
        node_c = LayoutNode(style=FlexStyle())

        node_a.add_child(node_b)
        node_b.add_child(node_c)

        # node_a is grandparent of node_c
        with pytest.raises(ValueError, match=r"[Cc]ircular"):
            node_c.add_child(node_a)
