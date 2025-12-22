"""Tests for SemanticLocator text-based element finding."""

from wtfui.core.protocol import RenderNode
from wtfui.tui.layout.node import LayoutNode, LayoutResult
from wtfui.tui.layout.style import FlexStyle


class TestSemanticLocator:
    """Test SemanticLocator for finding elements by text."""

    def test_find_by_text_returns_node_with_matching_text_content(self):
        """Should find RenderNode with matching text_content."""
        from wtfui.tui.testing.locator import SemanticLocator

        # Build a simple render tree
        root = RenderNode(tag="div", element_id=1)
        child = RenderNode(tag="span", element_id=2, text_content="Hello World")
        root.children = [child]

        # Build element_to_layout mapping (simulating TUIRuntime._element_to_layout)
        root_layout = LayoutNode(style=FlexStyle())
        root_layout.layout = LayoutResult(x=0, y=0, width=100, height=50)
        child_layout = LayoutNode(style=FlexStyle())
        child_layout.layout = LayoutResult(x=10, y=10, width=80, height=20)
        root_layout.children = [child_layout]

        element_to_layout = {1: root_layout, 2: child_layout}

        locator = SemanticLocator(render_tree=root, element_to_layout=element_to_layout)
        found = locator.find_by_text("Hello World")

        assert found is not None
        assert found.text_content == "Hello World"

    def test_find_by_text_returns_node_with_matching_label(self):
        """Should find RenderNode with matching label (for buttons)."""
        from wtfui.tui.testing.locator import SemanticLocator

        root = RenderNode(tag="div", element_id=1)
        button = RenderNode(tag="button", element_id=2, label="Click Me")
        root.children = [button]

        root_layout = LayoutNode(style=FlexStyle())
        root_layout.layout = LayoutResult(x=0, y=0, width=100, height=50)
        button_layout = LayoutNode(style=FlexStyle())
        button_layout.layout = LayoutResult(x=10, y=10, width=60, height=20)
        root_layout.children = [button_layout]

        element_to_layout = {1: root_layout, 2: button_layout}

        locator = SemanticLocator(render_tree=root, element_to_layout=element_to_layout)
        found = locator.find_by_text("Click Me")

        assert found is not None
        assert found.label == "Click Me"

    def test_find_by_text_returns_none_when_not_found(self):
        """Should return None when no matching text found."""
        from wtfui.tui.testing.locator import SemanticLocator

        root = RenderNode(tag="div", element_id=1, text_content="Other Text")
        root_layout = LayoutNode(style=FlexStyle())
        root_layout.layout = LayoutResult(x=0, y=0, width=100, height=50)

        element_to_layout = {1: root_layout}

        locator = SemanticLocator(render_tree=root, element_to_layout=element_to_layout)
        found = locator.find_by_text("Not Found")

        assert found is None

    def test_find_by_text_partial_match(self):
        """Should support partial text matching."""
        from wtfui.tui.testing.locator import SemanticLocator

        root = RenderNode(tag="span", element_id=1, text_content="Count: 42")
        root_layout = LayoutNode(style=FlexStyle())
        root_layout.layout = LayoutResult(x=0, y=0, width=100, height=20)

        element_to_layout = {1: root_layout}

        locator = SemanticLocator(render_tree=root, element_to_layout=element_to_layout)
        found = locator.find_by_text("Count:", partial=True)

        assert found is not None
        assert "Count:" in found.text_content

    def test_get_absolute_bounds_for_root(self):
        """get_absolute_bounds() should return correct coords for root (no parent)."""
        from wtfui.tui.testing.locator import SemanticLocator

        root = RenderNode(tag="span", element_id=42, text_content="Target")
        root_layout = LayoutNode(style=FlexStyle())
        root_layout.layout = LayoutResult(x=15, y=25, width=80, height=30)
        root_layout.parent = None  # Root has no parent

        element_to_layout = {42: root_layout}

        locator = SemanticLocator(render_tree=root, element_to_layout=element_to_layout)
        found = locator.find_by_text("Target")
        bounds = locator.get_absolute_bounds(found)

        assert bounds == (15, 25, 80, 30)

    def test_get_absolute_bounds_for_nested_element(self):
        """CRITICAL: get_absolute_bounds() must traverse parent chain.

        This test catches the "relative coordinate trap" bug.
        """
        from wtfui.tui.testing.locator import SemanticLocator

        # Container at (20, 20)
        container = RenderNode(tag="div", element_id=1)
        container_layout = LayoutNode(style=FlexStyle())
        container_layout.layout = LayoutResult(x=20, y=20, width=200, height=200)
        container_layout.parent = None

        # Button at (10, 10) RELATIVE to container = ABSOLUTE (30, 30)
        button = RenderNode(tag="button", element_id=2, label="Click Me")
        button_layout = LayoutNode(style=FlexStyle())
        button_layout.layout = LayoutResult(x=10, y=10, width=60, height=20)
        button_layout.parent = container_layout  # Parent reference!

        container.children = [button]
        container_layout.children = [button_layout]

        element_to_layout = {1: container_layout, 2: button_layout}

        locator = SemanticLocator(render_tree=container, element_to_layout=element_to_layout)
        found = locator.find_by_text("Click Me")
        bounds = locator.get_absolute_bounds(found)

        # Expected: (20+10, 20+10, 60, 20) = (30, 30, 60, 20)
        assert bounds == (30, 30, 60, 20)
