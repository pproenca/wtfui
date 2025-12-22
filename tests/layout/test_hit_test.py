"""Tests for hit_test functionality on LayoutNode."""

from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import FlexStyle


class TestHitTestBasic:
    """Test basic hit_test coordinate detection."""

    def test_hit_test_returns_node_when_inside_bounds(self):
        """Point inside node bounds returns the node."""
        node = LayoutNode(style=FlexStyle())
        node.layout = LayoutResult(x=10, y=10, width=50, height=30)

        result = node.hit_test(25, 20)

        assert result is node

    def test_hit_test_returns_none_when_outside_bounds(self):
        """Point outside node bounds returns None."""
        node = LayoutNode(style=FlexStyle())
        node.layout = LayoutResult(x=10, y=10, width=50, height=30)

        result = node.hit_test(5, 5)  # Left of node

        assert result is None

    def test_hit_test_edge_cases(self):
        """Test boundary conditions: left/top edge inclusive, right/bottom exclusive."""
        node = LayoutNode(style=FlexStyle())
        node.layout = LayoutResult(x=10, y=10, width=50, height=30)

        # Left edge (x=10) should be inside
        assert node.hit_test(10, 20) is node
        # Top edge (y=10) should be inside
        assert node.hit_test(25, 10) is node
        # Right edge (x=60) should be outside
        assert node.hit_test(60, 20) is None
        # Bottom edge (y=40) should be outside
        assert node.hit_test(25, 40) is None


class TestHitTestNested:
    """Test hit_test with nested children."""

    def test_hit_test_returns_deepest_child(self):
        """Point inside nested child returns the child, not parent."""
        parent = LayoutNode(style=FlexStyle())
        parent.layout = LayoutResult(x=0, y=0, width=100, height=100)

        child = LayoutNode(style=FlexStyle())
        child.layout = LayoutResult(x=20, y=20, width=40, height=40)
        parent.children = [child]

        # Point inside child (absolute coords: 30, 30)
        result = parent.hit_test(30, 30)
        assert result is child

        # Point inside parent but outside child
        result = parent.hit_test(5, 5)
        assert result is parent

    def test_hit_test_respects_z_order(self):
        """Later children (higher z-index) are hit first."""
        parent = LayoutNode(style=FlexStyle())
        parent.layout = LayoutResult(x=0, y=0, width=100, height=100)

        child1 = LayoutNode(style=FlexStyle())
        child1.layout = LayoutResult(x=10, y=10, width=50, height=50)

        child2 = LayoutNode(style=FlexStyle())
        child2.layout = LayoutResult(x=30, y=30, width=50, height=50)

        parent.children = [child1, child2]

        # Point in overlapping region should hit child2 (topmost)
        result = parent.hit_test(40, 40)
        assert result is child2

        # Point only in child1
        result = parent.hit_test(15, 15)
        assert result is child1

    def test_hit_test_coordinate_translation_deeply_nested(self):
        """CRITICAL: Test coordinate translation for deeply nested nodes."""
        # Root at absolute (10, 10)
        root = LayoutNode(style=FlexStyle())
        root.layout = LayoutResult(x=10, y=10, width=100, height=100)

        # Child at (5, 5) RELATIVE to root = absolute (15, 15)
        child = LayoutNode(style=FlexStyle())
        child.layout = LayoutResult(x=5, y=5, width=50, height=50)
        root.children = [child]

        # Grandchild at (10, 10) RELATIVE to child = absolute (25, 25)
        grandchild = LayoutNode(style=FlexStyle())
        grandchild.layout = LayoutResult(x=10, y=10, width=20, height=20)
        child.children = [grandchild]

        # Click at absolute (30, 30) should hit grandchild
        result = root.hit_test(30, 30)
        assert result is grandchild

        # Click at absolute (16, 16) should hit child (not grandchild)
        result = root.hit_test(16, 16)
        assert result is child

        # Click at absolute (11, 11) should hit root (not child)
        result = root.hit_test(11, 11)
        assert result is root
