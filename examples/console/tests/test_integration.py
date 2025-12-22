"""Integration tests for console demo components."""


class TestConsoleIntegration:
    """Integration tests for the component-based console demo."""

    def test_all_components_import(self) -> None:
        """All components should import without error."""
        from components import Dashboard, ProcessList, ProgressBar
        from state import SystemState

        assert callable(Dashboard)
        assert callable(ProcessList)
        assert callable(ProgressBar)
        assert SystemState is not None

    def test_state_signals_work(self) -> None:
        """SystemState Signals should notify subscribers."""
        from state import SystemState

        state = SystemState()
        updates = []
        state.cpu_percent.subscribe(lambda: updates.append(("cpu", state.cpu_percent.value)))
        state.memory_percent.subscribe(lambda: updates.append(("mem", state.memory_percent.value)))

        state.cpu_percent.value = 50.0
        state.memory_percent.value = 75.0

        assert ("cpu", 50.0) in updates
        assert ("mem", 75.0) in updates

    def test_style_module_imports(self) -> None:
        """Style module should be usable."""
        from wtfui.core.style import Colors, Style

        s = Style(color="white", bg=Colors.Slate._900)
        assert s.color == "white"
        assert s.bg == "slate-900"

    def test_run_tui_importable(self) -> None:
        """run_tui should be importable."""
        from wtfui.tui.renderer import run_tui

        assert callable(run_tui)

    def test_poll_stats_is_async(self) -> None:
        """Verify poll_stats is async (Council correction)."""
        import inspect

        from components.dashboard import _poll_stats

        assert inspect.iscoroutinefunction(_poll_stats)
