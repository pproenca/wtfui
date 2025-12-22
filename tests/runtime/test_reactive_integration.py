"""Integration tests for reactive layout in TUIRuntime."""

import pytest

from wtfui.core.signal import Signal
from wtfui.tui.runtime import TUIRuntime
from wtfui.ui.elements import Div


@pytest.fixture
def mock_terminal(monkeypatch):
    """Mock terminal size."""
    monkeypatch.setattr("shutil.get_terminal_size", lambda fallback=(80, 24): (80, 24))


class TestReactiveLayoutIntegration:
    def test_signal_change_triggers_layout_dirty(self, mock_terminal):
        """When a Signal-bound prop changes, runtime becomes dirty."""
        width = Signal(100)

        async def app():
            return Div(width=width)

        runtime = TUIRuntime(app)
        runtime.element_tree = Div(width=width)

        # Initial layout
        runtime._update_layout()
        assert runtime.reactive_layout is not None

        # Clear dirty state
        runtime.reactive_layout.clear_dirty_recursive()
        runtime.is_dirty = False

        # Change signal
        width.value = 200

        # Runtime should be dirty
        assert runtime.is_dirty is True
        assert runtime.reactive_layout.is_dirty() is True

    def test_full_cycle_signal_to_layout(self, mock_terminal):
        """Full cycle: Signal change -> dirty -> _update_layout -> new layout."""
        width = Signal(100)

        async def app():
            return Div(width=width)

        runtime = TUIRuntime(app)
        runtime.element_tree = Div(width=width)

        # Initial layout
        runtime._update_layout()
        initial_layout = runtime.layout_root

        # Clear and change
        runtime.reactive_layout.clear_dirty_recursive()
        runtime.is_dirty = False
        width.value = 200

        # Update layout (should recompute)
        runtime._update_layout()

        # New layout should have updated width
        assert runtime.layout_root is not initial_layout
        assert runtime.layout_root.style.width.value == 200.0

    def test_no_signal_change_no_recompute(self, mock_terminal):
        """Without Signal changes, layout is not recomputed."""

        async def app():
            return Div(width=100)

        runtime = TUIRuntime(app)
        runtime.element_tree = Div(width=100)

        # Initial layout
        runtime._update_layout()

        # Clear dirty
        runtime.reactive_layout.clear_dirty_recursive()
        runtime.is_dirty = False

        # Update without signal change
        runtime._update_layout()

        # Layout should NOT have been recomputed (is_dirty still False)
        assert runtime.is_dirty is False

    def test_nested_signal_triggers_parent_dirty(self, mock_terminal):
        """Nested Signal change propagates dirty to parent."""
        child_width = Signal(50)

        async def app():
            pass

        runtime = TUIRuntime(app)

        # Manually build element tree with nested signal
        with Div() as parent:
            Div(width=child_width)
        runtime.element_tree = parent

        # Initial layout
        runtime._update_layout()
        runtime.reactive_layout.clear_dirty_recursive()
        runtime.is_dirty = False

        # Change child signal
        child_width.value = 100

        # Runtime should be dirty
        assert runtime.is_dirty is True
        # Parent reactive node should be dirty (propagation)
        assert runtime.reactive_layout.is_dirty() is True

    def test_dispose_stops_signal_updates(self, mock_terminal):
        """After dispose, Signal changes don't affect runtime."""
        width = Signal(100)

        async def app():
            return Div(width=width)

        runtime = TUIRuntime(app)
        runtime.element_tree = Div(width=width)

        # Initial layout
        runtime._update_layout()
        runtime.is_dirty = False

        # Dispose
        runtime._dispose_layout()

        # Change signal
        width.value = 200

        # Runtime should NOT be dirty (disposed)
        assert runtime.is_dirty is False
        assert runtime.reactive_layout is None
