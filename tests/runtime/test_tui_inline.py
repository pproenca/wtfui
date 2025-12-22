"""Tests for TUIRuntime inline mode."""

import contextlib
from unittest.mock import MagicMock, patch


def test_tui_runtime_accepts_inline_parameter():
    """TUIRuntime should accept inline=True parameter."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app, inline=True)
    assert runtime.inline is True


def test_tui_runtime_inline_default_false():
    """TUIRuntime inline should default to False."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)
    assert runtime.inline is False


def test_tui_runtime_start_uses_inline_terminal_context():
    """TUIRuntime.start() should pass inline to TerminalContext."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app, inline=True, fps=1)

    with patch("wtfui.tui.renderer.terminal.TerminalContext") as mock_ctx:
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_ctx.return_value)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=None)
        mock_ctx.return_value.width = 80
        mock_ctx.return_value.height = 24

        # Mock asyncio.run to prevent actual execution
        with patch("asyncio.run"), contextlib.suppress(Exception):
            runtime.start()

    # Verify TerminalContext was called with inline=True
    mock_ctx.assert_called_once()
    call_kwargs = mock_ctx.call_args.kwargs
    assert call_kwargs.get("inline") is True, "Should pass inline=True to TerminalContext"


def test_tui_runtime_inline_uses_large_height_for_layout():
    """Inline mode should compute layout with large available height."""
    from wtfui.core.context import reset_parent, set_current_parent
    from wtfui.tui.runtime import TUIRuntime
    from wtfui.ui import Text, VStack

    captured_size = []

    original_compute_layout = None

    def capturing_compute_layout(node, available):
        captured_size.append(available)
        # Call original to allow layout to work
        return original_compute_layout(node, available)

    def app():
        with VStack():
            Text("Line 1")
            Text("Line 2")

    runtime = TUIRuntime(app, inline=True)
    runtime.term_width = 80
    runtime.term_height = 24

    # Build element tree directly (simulating what _run_event_loop does)
    class _Capture:
        def __init__(self):
            self.children = []

        def invalidate_layout(self):
            pass

    capture = _Capture()
    token = set_current_parent(capture)
    try:
        app()
    finally:
        reset_parent(token)

    if capture.children:
        runtime.element_tree = capture.children[0]

    # Import original and patch
    from wtfui.tui.layout import compute as compute_module

    original_compute_layout = compute_module.compute_layout

    with patch.object(compute_module, "compute_layout", side_effect=capturing_compute_layout):
        runtime._update_layout()

    # Verify compute_layout was called and captured the size
    assert len(captured_size) > 0, "compute_layout should be called"
    available_size = captured_size[0]
    # In inline mode, height should be very large (effectively infinite)
    assert available_size.height >= 10000, (
        f"Inline mode should use large height, got {available_size.height}"
    )


def test_render_frame_uses_original_stdout_not_proxy():
    """_render_frame should write to original stdout, not OutputProxy, to avoid recursion."""
    import sys
    from io import StringIO
    from unittest.mock import MagicMock, patch

    from wtfui.tui.renderer.output import OutputProxy
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        from wtfui.ui.elements import Div, Text

        with Div():
            Text("test")

    runtime = TUIRuntime(dummy_app, inline=True)

    # Create a mock renderer
    mock_renderer = MagicMock()
    mock_renderer.flush.return_value = "test output"
    mock_renderer.get_clear_sequence.return_value = "\x1b[2J"
    mock_renderer.repaint.return_value = "repaint output"
    runtime.renderer = mock_renderer

    # Create fake stdout that is an OutputProxy
    original_stdout = StringIO()
    proxy = OutputProxy(original_stdout, mock_renderer, runtime.render_lock)

    # Track what gets written to what
    proxy_write_called = False

    original_proxy_write = proxy.write

    def tracking_proxy_write(data):
        nonlocal proxy_write_called
        proxy_write_called = True
        return original_proxy_write(data)

    proxy.write = tracking_proxy_write

    # Set up minimal state for _render_frame to run
    from wtfui.core.element import Element
    from wtfui.tui.builder import RenderTreeBuilder

    runtime.element_tree = Element()
    runtime.layout_root = MagicMock()
    runtime.needs_rebuild = False

    # Mock the build_with_layout to avoid layout coordinate issues
    mock_render_node = MagicMock()
    with patch.object(RenderTreeBuilder, "build_with_layout", return_value=mock_render_node):
        with patch.object(sys, "stdout", proxy):
            with patch.object(sys, "__stdout__", original_stdout):
                runtime._render_frame()

    # The proxy's write method should NOT have been called
    # because _render_frame should bypass it
    assert not proxy_write_called, "_render_frame should bypass OutputProxy to avoid recursion"
