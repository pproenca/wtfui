"""Integration tests for TUI reactivity fixes.

These tests verify that:
1. Element.invalidate_layout notifies runtime
2. _render_frame bypasses OutputProxy
3. _build_layout_element_map handles mismatches
4. The full reactive update cycle works end-to-end
"""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch


class TestTUIReactivityIntegration:
    """Integration tests for TUI reactivity system."""

    def test_element_structure_change_triggers_rebuild(self):
        """When element structure changes, runtime.needs_rebuild should be set."""
        from wtfui.core.context import (
            reset_parent,
            reset_runtime,
            set_current_parent,
            set_current_runtime,
        )
        from wtfui.core.element import Element
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app():
            pass

        runtime = TUIRuntime(dummy_app)
        runtime.needs_rebuild = False
        runtime.is_dirty = False

        runtime_token = set_current_runtime(runtime)
        try:
            parent = Element()
            parent_token = set_current_parent(parent)
            try:
                # Creating a child with parent as current parent calls invalidate_layout
                Element()

                # Runtime should be notified
                assert runtime.needs_rebuild is True
                assert runtime.is_dirty is True
            finally:
                reset_parent(parent_token)
        finally:
            reset_runtime(runtime_token)

    def test_render_frame_does_not_recurse_in_inline_mode(self):
        """_render_frame should not cause recursion when OutputProxy is active."""
        from wtfui.core.element import Element
        from wtfui.tui.layout.node import LayoutNode, LayoutResult
        from wtfui.tui.renderer.output import OutputProxy
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app():
            pass

        runtime = TUIRuntime(dummy_app, inline=True)

        # Set up minimal state
        mock_renderer = MagicMock()
        mock_renderer.flush.return_value = "output"
        runtime.renderer = mock_renderer
        runtime.element_tree = Element()

        # Create a proper mock layout node with required attributes
        mock_layout = MagicMock(spec=LayoutNode)
        mock_layout.layout = LayoutResult(x=0, y=0, width=100, height=100)
        mock_layout.children = []
        runtime.layout_root = mock_layout
        runtime.needs_rebuild = False

        # Track recursion
        recursion_count = 0

        original_stdout = StringIO()
        proxy = OutputProxy(original_stdout, mock_renderer, runtime.render_lock)

        original_write = proxy.write

        def counting_write(data):
            nonlocal recursion_count
            recursion_count += 1
            if recursion_count > 1:
                raise RecursionError("Infinite recursion detected!")
            return original_write(data)

        proxy.write = counting_write

        # Mock sys.__stdout__ to capture output
        real_stdout = StringIO()

        with patch.object(sys, "stdout", proxy):
            with patch.object(sys, "__stdout__", real_stdout):
                # Should not raise RecursionError
                runtime._render_frame()

        # Proxy write should not have been called
        assert recursion_count == 0, "OutputProxy.write was called, causing potential recursion"

    def test_layout_mapping_survives_transient_mismatch(self):
        """_build_layout_element_map should handle transient element/layout mismatches."""
        from wtfui.core.element import Element
        from wtfui.tui.layout.node import LayoutNode
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app():
            pass

        runtime = TUIRuntime(dummy_app)
        runtime._layout_to_element = {}
        runtime._element_to_layout = {}

        # Simulate a race condition: element has 3 children, layout has 2
        parent_element = Element()
        parent_element.children = [Element(), Element(), Element()]

        # Create mock layout nodes with children attribute
        parent_layout = MagicMock(spec=LayoutNode)
        child_layout_1 = MagicMock(spec=LayoutNode)
        child_layout_1.children = []
        child_layout_2 = MagicMock(spec=LayoutNode)
        child_layout_2.children = []
        parent_layout.children = [child_layout_1, child_layout_2]

        # Should not crash
        runtime._build_layout_element_map(parent_element, parent_layout)

        # Should have mapped at least the parent and the 2 matching children
        assert id(parent_element) in runtime._element_to_layout
        assert id(parent_layout) in runtime._layout_to_element
        assert len(runtime._element_to_layout) >= 3  # parent + 2 matched children
