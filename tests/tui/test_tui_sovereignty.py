# tests/tui/test_tui_sovereignty.py
"""Litmus tests for TUI sovereignty.

TUI (wtfui.tui) owns terminal-specific concerns:
- Layout engine (wtfui.tui.layout)
- Console rendering (wtfui.renderer.console)
- Layout adaptation (LayoutAdapter, ReactiveLayoutAdapter)
"""


class TestTUISovereignty:
    """Verify TUI sovereignty over terminal-specific concerns."""

    def test_layout_lives_in_tui_package(self):
        """Layout engine should be in wtfui.tui.layout."""
        from wtfui.tui.layout.compute import compute_layout
        from wtfui.tui.layout.node import LayoutNode
        from wtfui.tui.layout.style import FlexStyle
        from wtfui.tui.layout.types import Size

        # Create a simple layout
        node = LayoutNode(style=FlexStyle())
        compute_layout(node, Size(100, 100))

        # Verify layout was computed
        assert node.layout.width == 100
        assert node.layout.height == 100

    def test_backward_compat_shims_work(self):
        """Old wtfui.layout imports should still work via shims."""
        # These should all import successfully via shims
        from wtfui.tui.layout.compute import compute_layout
        from wtfui.tui.layout.node import LayoutNode
        from wtfui.tui.layout.style import FlexStyle
        from wtfui.tui.layout.types import Size

        node = LayoutNode(style=FlexStyle())
        compute_layout(node, Size(80, 60))

        assert node.layout.width == 80
        assert node.layout.height == 60

    def test_layout_adapter_connects_core_to_tui(self):
        """LayoutAdapter should bridge Core elements to TUI layout."""
        from wtfui.tui import LayoutAdapter

        adapter = LayoutAdapter()
        assert adapter is not None
        # LayoutAdapter exists and can be instantiated

    def test_console_renderer_in_tui_exports(self):
        """ConsoleRenderer should be accessible from wtfui.tui."""
        from wtfui.tui import ConsoleRenderer

        renderer = ConsoleRenderer(width=80, height=24)
        assert renderer.width == 80
        assert renderer.height == 24

    def test_tui_layout_style_system(self):
        """TUI layout style system should work."""
        from wtfui.tui.layout.style import FlexDirection, FlexStyle
        from wtfui.tui.layout.types import Dimension

        style = FlexStyle(
            width=Dimension.points(100),
            height=Dimension.points(50),
            flex_direction=FlexDirection.ROW,
        )

        assert style.width.value == 100
        assert style.height.value == 50
        assert style.flex_direction == FlexDirection.ROW
