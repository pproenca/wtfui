"""Tests for SystemState reactive state management."""


class TestSystemState:
    """Test SystemState Signal properties."""

    def test_cpu_percent_is_signal(self) -> None:
        """cpu_percent should be a Signal."""
        from state import SystemState

        from wtfui import Signal

        state = SystemState()
        assert isinstance(state.cpu_percent, Signal)

    def test_cpu_percent_default_value(self) -> None:
        """cpu_percent should default to 0.0."""
        from state import SystemState

        state = SystemState()
        assert state.cpu_percent.value == 0.0

    def test_processes_is_signal(self) -> None:
        """processes should be a Signal containing a list."""
        from state import SystemState

        from wtfui import Signal

        state = SystemState()
        assert isinstance(state.processes, Signal)
        assert state.processes.value == []

    def test_filter_text_is_signal(self) -> None:
        """filter_text should be a Signal for UI binding."""
        from state import SystemState

        from wtfui import Signal

        state = SystemState()
        assert isinstance(state.filter_text, Signal)
        assert state.filter_text.value == ""

    def test_signal_update_notifies(self) -> None:
        """Updating a signal value should notify subscribers."""
        from state import SystemState

        state = SystemState()
        notifications = []
        state.cpu_percent.subscribe(lambda: notifications.append(state.cpu_percent.value))

        state.cpu_percent.value = 50.0

        assert 50.0 in notifications
