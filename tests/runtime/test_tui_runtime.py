"""Tests for TUIRuntime class."""

import asyncio
import inspect

import pytest


class TestTUIRuntimeInit:
    """Test TUIRuntime initialization."""

    def test_tui_runtime_importable(self) -> None:
        """TUIRuntime should be importable from wtfui.tui.runtime."""
        from wtfui.tui.runtime import TUIRuntime

        assert TUIRuntime is not None

    def test_tui_runtime_accepts_app_factory(self) -> None:
        """TUIRuntime should accept an app_factory callable."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert runtime.app_factory is dummy_app

    def test_tui_runtime_has_required_attributes(self) -> None:
        """TUIRuntime should have layout state and threading primitives."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)

        # Layout state
        assert hasattr(runtime, "layout_root")
        assert runtime.layout_root is None

        # Threading primitives
        assert hasattr(runtime, "render_lock")
        assert hasattr(runtime, "is_dirty")
        assert hasattr(runtime, "running")


class TestInputThread:
    """Test input thread worker."""

    def test_runtime_has_event_queue(self) -> None:
        """TUIRuntime should have an event queue for thread communication."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "event_queue")
        assert isinstance(runtime.event_queue, asyncio.Queue)

    def test_runtime_has_input_worker_method(self) -> None:
        """TUIRuntime should have _input_worker method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_input_worker")
        assert callable(runtime._input_worker)


class TestEventBridge:
    """Test async event consumption."""

    def test_runtime_has_consume_events_method(self) -> None:
        """TUIRuntime should have _consume_events async method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_consume_events")
        assert inspect.iscoroutinefunction(runtime._consume_events)

    def test_runtime_has_handle_event_method(self) -> None:
        """TUIRuntime should have _handle_event async method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_handle_event")
        assert inspect.iscoroutinefunction(runtime._handle_event)


class TestMainLoop:
    """Test main async loop."""

    def test_runtime_has_main_loop_method(self) -> None:
        """TUIRuntime should have _main_loop async method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_main_loop")
        assert inspect.iscoroutinefunction(runtime._main_loop)

    def test_runtime_has_resolve_app_method(self) -> None:
        """TUIRuntime should have _resolve_app async method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_resolve_app")
        assert inspect.iscoroutinefunction(runtime._resolve_app)

    @pytest.mark.asyncio
    async def test_resolve_app_calls_sync_factory(self) -> None:
        """_resolve_app should call sync app factory."""
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text

        call_count = 0

        def counting_app() -> None:
            nonlocal call_count
            call_count += 1
            Text("Test")

        runtime = TUIRuntime(app_factory=counting_app)
        runtime.running = True
        await runtime._resolve_app()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_app_calls_async_factory(self) -> None:
        """_resolve_app should call async app factory."""
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text

        call_count = 0

        async def async_counting_app() -> None:
            nonlocal call_count
            call_count += 1
            Text("Async Test")

        runtime = TUIRuntime(app_factory=async_counting_app)
        runtime.running = True
        await runtime._resolve_app()

        assert call_count == 1


class TestLayoutLifecycle:
    """Test layout lifecycle management (disposal prevents memory leaks)."""

    def test_runtime_has_dispose_layout_method(self) -> None:
        """TUIRuntime should have _dispose_layout method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_dispose_layout")
        assert callable(runtime._dispose_layout)

    def test_dispose_layout_calls_dispose_on_reactive_nodes(self) -> None:
        """_dispose_layout should call dispose() on ReactiveLayoutNodes."""
        from unittest.mock import MagicMock

        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)

        # Create mock reactive layout tree with dispose method
        mock_node = MagicMock()
        mock_node.children = []
        mock_node.dispose = MagicMock()

        runtime.reactive_layout = mock_node
        runtime._dispose_layout()

        mock_node.dispose.assert_called_once()
        assert runtime.reactive_layout is None
        assert runtime.layout_root is None

    def test_dispose_layout_walks_children(self) -> None:
        """_dispose_layout should recursively dispose all children."""
        from unittest.mock import MagicMock

        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)

        # Create mock reactive tree: root -> child1, child2
        mock_child1 = MagicMock()
        mock_child1.children = []
        mock_child1.dispose = MagicMock()

        mock_child2 = MagicMock()
        mock_child2.children = []
        mock_child2.dispose = MagicMock()

        mock_root = MagicMock()
        mock_root.children = [mock_child1, mock_child2]
        mock_root.dispose = MagicMock()

        runtime.reactive_layout = mock_root
        runtime._dispose_layout()

        mock_root.dispose.assert_called_once()
        mock_child1.dispose.assert_called_once()
        mock_child2.dispose.assert_called_once()

    def test_update_layout_disposes_old_tree_first(self) -> None:
        """_dispose_layout should dispose reactive tree when called."""
        from typing import ClassVar
        from unittest.mock import MagicMock

        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Hello")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.running = True
        runtime.term_width = 80
        runtime.term_height = 24

        # Create initial element tree
        from wtfui.core.context import reset_parent, set_current_parent

        class _Capture:
            children: ClassVar[list] = []

            def invalidate_layout(self) -> None:
                """No-op invalidation for capture (not a real element)."""
                pass

        capture = _Capture()
        token = set_current_parent(capture)
        simple_app()
        reset_parent(token)
        runtime.element_tree = capture.children[0] if capture.children else None

        # First layout builds reactive tree
        runtime._update_layout()
        reactive_tree = runtime.reactive_layout

        assert reactive_tree is not None

        # Mock dispose on reactive tree
        dispose_mock = MagicMock()
        reactive_tree.dispose = dispose_mock

        # Calling _dispose_layout should dispose reactive tree
        runtime._dispose_layout()

        dispose_mock.assert_called_once()
        assert runtime.reactive_layout is None


class TestRenderIntegration:
    """Test ConsoleRenderer integration."""

    def test_runtime_has_render_frame_method(self) -> None:
        """TUIRuntime should have _render_frame method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "_render_frame")
        assert callable(runtime._render_frame)

    def test_runtime_has_renderer_attribute(self) -> None:
        """TUIRuntime should have renderer attribute."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "renderer")

    def test_render_frame_produces_ansi_output(self) -> None:
        """_render_frame should produce ANSI output."""
        from io import StringIO
        from typing import ClassVar
        from unittest.mock import patch

        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Hello")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.renderer = ConsoleRenderer(width=40, height=10)
        runtime.running = True
        runtime.term_width = 40
        runtime.term_height = 10

        # Build element tree manually
        from wtfui.core.context import reset_parent, set_current_parent

        class _Capture:
            children: ClassVar[list] = []

            def invalidate_layout(self) -> None:
                """No-op invalidation for capture (not a real element)."""
                pass

        capture = _Capture()
        token = set_current_parent(capture)
        simple_app()
        reset_parent(token)
        runtime.element_tree = capture.children[0] if capture.children else None

        # Update layout
        runtime._update_layout()

        # Capture stdout - need to patch both sys.stdout and sys.__stdout__
        # because _render_frame uses sys.__stdout__ to bypass OutputProxy
        output = StringIO()
        with patch("sys.stdout", output):
            with patch("sys.__stdout__", output):
                runtime._render_frame()

        result = output.getvalue()
        # Should produce some output
        assert len(result) > 0


class TestResizeHandling:
    """Test terminal resize handling."""

    @pytest.mark.asyncio
    async def test_handle_event_processes_resize(self) -> None:
        """_handle_event should process ResizeEvent."""
        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.renderer.input import ResizeEvent
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Resize test")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.renderer = ConsoleRenderer(width=80, height=24)
        runtime.running = True
        runtime.term_width = 80
        runtime.term_height = 24

        # Send resize event
        resize_event = ResizeEvent(width=100, height=30)
        await runtime._handle_event(resize_event)

        # Check dimensions updated
        assert runtime.term_width == 100
        assert runtime.term_height == 30
        assert runtime.is_dirty is True


def test_runtime_has_reactive_layout_field():
    """TUIRuntime has reactive_layout field initialized to None."""
    from wtfui.tui.runtime import TUIRuntime

    async def app():
        pass

    runtime = TUIRuntime(app)
    assert hasattr(runtime, "reactive_layout")
    assert runtime.reactive_layout is None


class TestPublicAPI:
    """Test public API."""

    def test_runtime_has_start_method(self) -> None:
        """TUIRuntime should have start method."""
        from wtfui.tui.runtime import TUIRuntime

        def dummy_app() -> None:
            pass

        runtime = TUIRuntime(app_factory=dummy_app)
        assert hasattr(runtime, "start")
        assert callable(runtime.start)

    def test_run_tui_app_function_exists(self) -> None:
        """run_tui_app convenience function should exist."""
        from wtfui.tui.runtime import run_tui_app

        assert callable(run_tui_app)

    def test_run_alias_exists(self) -> None:
        """run alias should exist for CLI consistency."""
        from wtfui.tui.runtime import run

        assert callable(run)

    def test_tui_runtime_exportable_from_runtime_package(self) -> None:
        """TUIRuntime should be importable from wtfui.runtime."""
        from wtfui.tui.runtime import TUIRuntime

        assert TUIRuntime is not None


def test_hook_dirty_callback_sets_runtime_dirty():
    """_hook_dirty_callback makes Signal changes set runtime.is_dirty."""
    from wtfui.core.signal import Signal
    from wtfui.tui.layout.reactive import ReactiveLayoutNode
    from wtfui.tui.runtime import TUIRuntime

    async def app():
        pass

    runtime = TUIRuntime(app)
    runtime.is_dirty = False

    width = Signal(100)
    node = ReactiveLayoutNode(style_signals={"width": width})
    node.clear_dirty()

    # Hook the callback
    runtime._hook_dirty_callback(node)

    # Change signal should set runtime.is_dirty
    width.value = 200
    assert runtime.is_dirty is True


def test_hook_dirty_callback_recursive():
    """_hook_dirty_callback hooks all nodes in tree."""
    from wtfui.core.signal import Signal
    from wtfui.tui.layout.reactive import ReactiveLayoutNode
    from wtfui.tui.runtime import TUIRuntime

    async def app():
        pass

    runtime = TUIRuntime(app)
    runtime.is_dirty = False

    child_width = Signal(50)
    parent = ReactiveLayoutNode()
    child = ReactiveLayoutNode(style_signals={"width": child_width})
    parent.add_child(child)
    parent.clear_dirty_recursive()

    runtime._hook_dirty_callback(parent)

    # Child signal change should set runtime.is_dirty
    child_width.value = 100
    assert runtime.is_dirty is True


@pytest.fixture
def mock_terminal(monkeypatch):
    """Mock terminal size for TUIRuntime tests."""
    monkeypatch.setattr("shutil.get_terminal_size", lambda fallback=(80, 24): (80, 24))


def test_update_layout_builds_reactive_tree_once(mock_terminal):
    """_update_layout builds reactive tree only on first call."""
    from wtfui.tui.runtime import TUIRuntime
    from wtfui.ui.elements import Div

    async def app():
        return Div()

    runtime = TUIRuntime(app)

    # Simulate element tree being set (normally done by _resolve_app)
    runtime.element_tree = Div()

    # First update - should build reactive tree
    runtime._update_layout()
    first_reactive = runtime.reactive_layout

    assert first_reactive is not None

    # Mark not dirty to simulate no changes
    first_reactive.clear_dirty_recursive()

    # Second update - should NOT rebuild reactive tree
    runtime._update_layout()

    assert runtime.reactive_layout is first_reactive  # Same object


def test_update_layout_only_recomputes_when_dirty(mock_terminal):
    """_update_layout skips compute_layout when not dirty."""
    from wtfui.tui.runtime import TUIRuntime
    from wtfui.ui.elements import Div

    async def app():
        return Div()

    runtime = TUIRuntime(app)
    runtime.element_tree = Div()

    # First update
    runtime._update_layout()

    # Clear dirty - no recompute needed
    runtime.reactive_layout.clear_dirty_recursive()
    runtime.is_dirty = False

    # Second update - should skip
    runtime._update_layout()

    # is_dirty should remain False (no recompute happened)
    assert runtime.is_dirty is False


class TestFPSConfiguration:
    """Tests for FPS configuration parameter."""

    def test_tui_runtime_accepts_fps_parameter(self):
        """TUIRuntime should accept fps keyword argument."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app, fps=30)
        assert runtime.fps == 30

    def test_tui_runtime_default_fps_is_60(self):
        """TUIRuntime should default to 60 FPS."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app)
        assert runtime.fps == 60


class TestMouseConfiguration:
    """Tests for mouse tracking configuration."""

    def test_tui_runtime_accepts_mouse_parameter(self):
        """TUIRuntime should accept mouse keyword argument."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app, mouse=False)
        assert runtime.mouse is False

    def test_tui_runtime_default_mouse_is_true(self):
        """TUIRuntime should default to mouse=True."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app)
        assert runtime.mouse is True


class TestOnKeyCallback:
    """Tests for on_key callback support."""

    def test_tui_runtime_accepts_on_key_parameter(self):
        """TUIRuntime should accept on_key keyword argument."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        def handler(key: str) -> None:
            pass

        runtime = TUIRuntime(app, on_key=handler)
        assert runtime.on_key is handler

    def test_tui_runtime_default_on_key_is_none(self):
        """TUIRuntime should default to on_key=None."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app)
        assert runtime.on_key is None

    @pytest.mark.asyncio
    async def test_handle_event_calls_on_key_callback(self):
        """_handle_event should call on_key callback for key events."""
        from wtfui.tui.renderer.input import KeyEvent
        from wtfui.tui.runtime import TUIRuntime

        captured_keys: list[str] = []

        def capture_key(key: str) -> None:
            captured_keys.append(key)

        def app():
            pass

        runtime = TUIRuntime(app, on_key=capture_key)
        await runtime._handle_event(KeyEvent(key="x"))

        assert captured_keys == ["x"]

    @pytest.mark.asyncio
    async def test_on_key_called_before_quit_check(self):
        """on_key should be called even for 'q' key before runtime stops."""
        from wtfui.tui.renderer.input import KeyEvent
        from wtfui.tui.runtime import TUIRuntime

        captured_keys: list[str] = []

        def capture_key(key: str) -> None:
            captured_keys.append(key)

        def app():
            pass

        runtime = TUIRuntime(app, on_key=capture_key)
        runtime.running = True
        await runtime._handle_event(KeyEvent(key="q"))

        assert captured_keys == ["q"]
        assert runtime.running is False  # Still quits after callback

    @pytest.mark.asyncio
    async def test_on_key_callback_error_does_not_crash_runtime(self):
        """on_key callback errors should be logged, not crash runtime."""
        import io
        import sys

        from wtfui.tui.renderer.input import KeyEvent
        from wtfui.tui.runtime import TUIRuntime

        def bad_callback(key: str) -> None:
            raise ValueError("User code error")

        def app():
            pass

        runtime = TUIRuntime(app, on_key=bad_callback)
        runtime.running = True

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()

        try:
            # Should not raise
            await runtime._handle_event(KeyEvent(key="x"))
            stderr_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

        # Error should be logged
        assert "Error in on_key callback" in stderr_output
        assert "User code error" in stderr_output
        # Runtime should still be running (not crashed)
        assert runtime.running is True


class TestFPSValidation:
    """Tests for fps parameter validation."""

    def test_fps_zero_raises_value_error(self):
        """fps=0 should raise ValueError."""
        import pytest

        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        with pytest.raises(ValueError, match="fps must be positive"):
            TUIRuntime(app, fps=0)

    def test_fps_negative_raises_value_error(self):
        """Negative fps should raise ValueError."""
        import pytest

        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        with pytest.raises(ValueError, match="fps must be positive"):
            TUIRuntime(app, fps=-10)

    def test_fps_positive_is_accepted(self):
        """Positive fps should be accepted."""
        from wtfui.tui.runtime import TUIRuntime

        def app():
            pass

        runtime = TUIRuntime(app, fps=1)
        assert runtime.fps == 1

        runtime = TUIRuntime(app, fps=120)
        assert runtime.fps == 120


class TestRenderLockType:
    """Tests for render_lock thread safety."""

    def test_render_lock_is_rlock(self):
        """render_lock must be RLock to prevent deadlock during print()."""
        import threading
        from unittest.mock import MagicMock

        from wtfui.tui.runtime import TUIRuntime

        runtime = TUIRuntime(lambda: MagicMock())

        # RLock allows same thread to acquire multiple times
        assert isinstance(runtime.render_lock, type(threading.RLock()))

    def test_render_lock_can_be_reacquired_by_same_thread(self):
        """Same thread should be able to acquire render_lock twice (RLock behavior)."""
        from unittest.mock import MagicMock

        from wtfui.tui.runtime import TUIRuntime

        runtime = TUIRuntime(lambda: MagicMock())

        # Simulate: _render_frame acquires lock, then print() inside component tries again
        acquired_first = runtime.render_lock.acquire(blocking=False)
        assert acquired_first, "First acquire should succeed"

        acquired_second = runtime.render_lock.acquire(blocking=False)
        assert acquired_second, "Second acquire by same thread should succeed (RLock)"

        # Release both
        runtime.render_lock.release()
        runtime.render_lock.release()


class TestOutputRedirectorIntegration:
    """Tests for OutputRedirector integration in TUIRuntime."""

    def test_tui_runtime_uses_output_redirector_in_inline_mode(self):
        """TUIRuntime should install OutputRedirector when inline=True."""
        import sys
        from unittest.mock import MagicMock, patch

        from wtfui.tui.runtime import TUIRuntime

        # Create a minimal TUIRuntime with inline=True
        runtime = TUIRuntime(lambda: MagicMock(), inline=True)

        # Track stdout type during context
        stdout_types: list[str] = []

        # Mock the main loop to capture stdout type and exit immediately
        async def mock_main_loop() -> None:
            stdout_types.append(type(sys.stdout).__name__)
            runtime.running = False

        # Mock terminal context and asyncio.run
        with (
            patch("wtfui.tui.renderer.terminal.TerminalContext") as mock_ctx,
            patch("wtfui.tui.renderer.terminal.get_terminal_size", return_value=(80, 24)),
            patch("wtfui.tui.runtime.asyncio.run") as mock_asyncio_run,
        ):
            # Make TerminalContext work as context manager
            mock_ctx.return_value.__enter__ = MagicMock()
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            # Capture what asyncio.run receives and execute it
            def run_coro(coro):
                import asyncio

                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            mock_asyncio_run.side_effect = run_coro

            # Patch _main_loop
            runtime._main_loop = mock_main_loop

            runtime.start()

        # Verify stdout was OutputProxy during inline mode
        assert "OutputProxy" in stdout_types

    def test_tui_runtime_does_not_use_output_redirector_in_alt_screen_mode(self):
        """TUIRuntime should NOT install OutputRedirector when inline=False (alt screen)."""
        import sys
        from unittest.mock import MagicMock, patch

        from wtfui.tui.runtime import TUIRuntime

        # Create TUIRuntime with inline=False (alt screen mode)
        runtime = TUIRuntime(lambda: MagicMock(), inline=False)

        stdout_types: list[str] = []

        async def mock_main_loop() -> None:
            stdout_types.append(type(sys.stdout).__name__)
            runtime.running = False

        with (
            patch("wtfui.tui.renderer.terminal.TerminalContext") as mock_ctx,
            patch("wtfui.tui.renderer.terminal.get_terminal_size", return_value=(80, 24)),
            patch("wtfui.tui.runtime.asyncio.run") as mock_asyncio_run,
        ):
            mock_ctx.return_value.__enter__ = MagicMock()
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            def run_coro(coro):
                import asyncio

                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            mock_asyncio_run.side_effect = run_coro
            runtime._main_loop = mock_main_loop

            runtime.start()

        # stdout should NOT be OutputProxy in alt screen mode
        assert "OutputProxy" not in stdout_types


class TestRenderFrameRaceConditionGuard:
    """Tests for race condition guard in _render_frame.

    CRITICAL: When For._sync modifies element children between _update_layout
    and _render_frame, the layout tree is stale. _render_frame must skip
    rendering to prevent element/layout mismatch causing visual corruption.
    """

    def test_render_frame_skips_when_needs_rebuild_is_true(self):
        """_render_frame should skip rendering if needs_rebuild is True.

        This prevents the race condition where For._sync modifies element
        children between _update_layout and _render_frame.
        """
        from io import StringIO
        from typing import ClassVar
        from unittest.mock import patch

        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Hello")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.renderer = ConsoleRenderer(width=40, height=10)
        runtime.running = True

        # Build element tree manually
        from wtfui.core.context import reset_parent, set_current_parent

        class _Capture:
            children: ClassVar[list] = []

            def invalidate_layout(self) -> None:
                pass

        capture = _Capture()
        token = set_current_parent(capture)
        simple_app()
        reset_parent(token)
        runtime.element_tree = capture.children[0] if capture.children else None

        # Update layout (builds layout_root)
        runtime._update_layout()

        # Simulate race condition: For._sync set needs_rebuild after layout
        runtime.needs_rebuild = True

        # Capture stdout
        output = StringIO()
        with patch("sys.stdout", output):
            runtime._render_frame()

        # Should produce NO output (skipped rendering)
        result = output.getvalue()
        assert result == "", f"Expected no output when needs_rebuild=True, got: {result!r}"

    def test_render_frame_renders_when_needs_rebuild_is_false(self):
        """_render_frame should render normally when needs_rebuild=False."""
        from io import StringIO
        from typing import ClassVar
        from unittest.mock import patch

        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Hello")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.renderer = ConsoleRenderer(width=40, height=10)
        runtime.running = True

        from wtfui.core.context import reset_parent, set_current_parent

        class _Capture:
            children: ClassVar[list] = []

            def invalidate_layout(self) -> None:
                pass

        capture = _Capture()
        token = set_current_parent(capture)
        simple_app()
        reset_parent(token)
        runtime.element_tree = capture.children[0] if capture.children else None

        runtime._update_layout()

        # Ensure needs_rebuild is False
        runtime.needs_rebuild = False

        # Capture stdout - need to patch both sys.stdout and sys.__stdout__
        # because _render_frame uses sys.__stdout__ to bypass OutputProxy
        output = StringIO()
        with patch("sys.stdout", output):
            with patch("sys.__stdout__", output):
                runtime._render_frame()

        # Should produce output
        result = output.getvalue()
        assert len(result) > 0, "Expected ANSI output when needs_rebuild=False"

    def test_render_frame_does_not_clear_buffer_when_skipping(self):
        """_render_frame should not clear buffer when skipping due to needs_rebuild.

        This ensures we don't show a blank screen when skipping a frame.
        """
        from typing import ClassVar

        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.runtime import TUIRuntime
        from wtfui.ui import Text, VStack

        def simple_app() -> None:
            with VStack():
                Text("Hello")

        runtime = TUIRuntime(app_factory=simple_app)
        runtime.renderer = ConsoleRenderer(width=40, height=10)
        runtime.running = True

        from wtfui.core.context import reset_parent, set_current_parent

        class _Capture:
            children: ClassVar[list] = []

            def invalidate_layout(self) -> None:
                pass

        capture = _Capture()
        token = set_current_parent(capture)
        simple_app()
        reset_parent(token)
        runtime.element_tree = capture.children[0] if capture.children else None

        runtime._update_layout()

        # Pre-render a frame to populate the buffer
        import io
        from unittest.mock import patch

        with patch("sys.stdout", io.StringIO()):
            runtime.needs_rebuild = False
            runtime._render_frame()

        # Get buffer content after first render
        buffer_before = runtime.renderer.front_buffer.clone()

        # Now simulate race condition
        runtime.needs_rebuild = True

        with patch("sys.stdout", io.StringIO()):
            runtime._render_frame()

        # Buffer should NOT have been cleared (still has content)
        # Compare by checking a known cell has content
        cell_after = runtime.renderer.front_buffer.get(0, 0)
        cell_before = buffer_before.get(0, 0)
        assert cell_after.char == cell_before.char, "Buffer should not change when skipping"


class TestSIGWINCHHandling:
    """Tests for SIGWINCH signal handling."""

    def test_sigwinch_handler_registered_on_start(self):
        """TUIRuntime.start should register SIGWINCH handler on Unix."""
        import signal
        import sys
        from unittest.mock import MagicMock, patch

        from wtfui.tui.runtime import TUIRuntime

        if sys.platform == "win32":
            pytest.skip("SIGWINCH not available on Windows")

        runtime = TUIRuntime(lambda: MagicMock(), inline=False)

        original_handler = signal.getsignal(signal.SIGWINCH)
        handler_registered = False

        def track_signal(signum, handler):
            nonlocal handler_registered
            if signum == signal.SIGWINCH and handler is not signal.SIG_DFL:
                handler_registered = True
            return original_handler

        with (
            patch("wtfui.tui.renderer.terminal.TerminalContext") as mock_ctx,
            patch("wtfui.tui.renderer.terminal.get_terminal_size", return_value=(80, 24)),
            patch("wtfui.tui.runtime.asyncio.run", side_effect=lambda _: None),
            patch("signal.signal", side_effect=track_signal),
        ):
            mock_ctx.return_value.__enter__ = MagicMock()
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            runtime.start()

        assert handler_registered, "SIGWINCH handler should be registered"

    @pytest.mark.asyncio
    async def test_sigwinch_generates_resize_event(self):
        """SIGWINCH signal should inject ResizeEvent into event queue."""
        import asyncio
        import signal
        import sys
        from unittest.mock import MagicMock, patch

        from wtfui.tui.renderer.input import ResizeEvent
        from wtfui.tui.runtime import TUIRuntime

        if sys.platform == "win32":
            pytest.skip("SIGWINCH not available on Windows")

        runtime = TUIRuntime(lambda: MagicMock())
        runtime._loop = asyncio.get_running_loop()  # Use real event loop
        runtime.running = True

        # Capture the handler that gets registered
        captured_handler = None

        def capture_signal(signum, handler):
            nonlocal captured_handler
            if signum == signal.SIGWINCH:
                captured_handler = handler
            return signal.SIG_DFL

        # Patch get_terminal_size before registering handler
        with patch(
            "wtfui.tui.renderer.terminal.get_terminal_size",
            return_value=(120, 40),
        ):
            with patch("signal.signal", side_effect=capture_signal):
                # Simulate the signal registration that happens in start()
                runtime._register_sigwinch_handler()

            assert captured_handler is not None, "Handler should be captured"

            # Trigger the handler (patch is still active)
            captured_handler(signal.SIGWINCH, None)

        # Event should be in queue
        event = await runtime.event_queue.get()
        assert isinstance(event, ResizeEvent)
        assert event.width == 120
        assert event.height == 40
