"""Tests for layout node to element mapping in TUIRuntime."""

from wtfui.core.context import reset_parent, set_current_parent
from wtfui.tui.runtime import TUIRuntime
from wtfui.ui.elements import Div, Text


class _Capture:
    """Capture elements as children."""

    def __init__(self):
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def invalidate_layout(self):
        """No-op for testing."""
        pass


def simple_app():
    with Div() as root:
        Text("Hello")
    return root


class TestLayoutElementMapping:
    """Test mapping between LayoutNode and Element."""

    def test_runtime_has_layout_to_element_map(self):
        """TUIRuntime should have a _layout_to_element dictionary."""
        runtime = TUIRuntime(app_factory=simple_app)
        assert hasattr(runtime, "_layout_to_element")
        assert isinstance(runtime._layout_to_element, dict)

    def test_runtime_has_element_to_layout_map(self):
        """TUIRuntime should have a _element_to_layout dictionary (keyed by element_id)."""
        runtime = TUIRuntime(app_factory=simple_app)
        assert hasattr(runtime, "_element_to_layout")
        assert isinstance(runtime._element_to_layout, dict)

    def test_update_layout_populates_both_mappings(self):
        """After _update_layout, both mappings should contain entries."""
        runtime = TUIRuntime(app_factory=simple_app)
        runtime.running = True

        # Build element tree manually
        capture = _Capture()
        token = set_current_parent(capture)
        runtime.element_tree = simple_app()
        reset_parent(token)

        # Trigger layout computation
        runtime._update_layout()

        # Both mappings should be populated
        assert len(runtime._layout_to_element) > 0
        assert len(runtime._element_to_layout) > 0

        # Each layout node ID should map to an element
        for layout_id, element in runtime._layout_to_element.items():
            assert isinstance(layout_id, int)
            assert element is not None
            assert hasattr(element, "tag")
            # Verify bidirectional: element_id maps back to same layout
            layout_node = runtime._element_to_layout[id(element)]
            assert id(layout_node) == layout_id

    def test_build_layout_element_map_handles_length_mismatch_gracefully(self):
        """_build_layout_element_map should not crash when element/layout children mismatch."""
        from unittest.mock import MagicMock

        from wtfui.core.element import Element
        from wtfui.tui.layout.node import LayoutNode

        def dummy_app():
            pass

        runtime = TUIRuntime(dummy_app)
        runtime._layout_to_element = {}
        runtime._element_to_layout = {}

        # Create element with 2 children
        parent_element = Element()
        child_element_1 = Element()
        child_element_2 = Element()
        parent_element.children = [child_element_1, child_element_2]

        # Create layout with only 1 child (simulates race condition)
        parent_layout = MagicMock(spec=LayoutNode)
        child_layout_1 = MagicMock(spec=LayoutNode)
        child_layout_1.children = []  # No children on the leaf node
        parent_layout.children = [child_layout_1]

        # Should not raise ValueError, should handle gracefully
        try:
            runtime._build_layout_element_map(parent_element, parent_layout)
        except ValueError as e:
            if "zip" in str(e).lower():
                raise AssertionError("strict=True zip raised ValueError on length mismatch") from e
            raise

        # Parent should still be mapped even if children mismatch
        assert id(parent_element) in runtime._element_to_layout
        assert id(parent_layout) in runtime._layout_to_element
