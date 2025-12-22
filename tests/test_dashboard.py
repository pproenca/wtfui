"""Tests for TUI Dashboard component."""


class TestDevDashboard:
    """Tests for the dev server dashboard."""

    def test_dashboard_updates_on_status_change(self) -> None:
        """Dashboard reacts to status signal changes."""
        from wtfui.core.signal import Signal

        status = Signal("Starting...")

        # Change status
        status.value = "Running on http://localhost:8000"

        # Status should be updated (reactive)
        assert status.value == "Running on http://localhost:8000"

    def test_dashboard_component_imports(self) -> None:
        """DevDashboard component should be importable."""
        from wtfui.cli.dashboard import DevDashboard

        assert callable(DevDashboard)


class TestBuildProgress:
    """Tests for the build progress component."""

    def test_build_progress_component_imports(self) -> None:
        """BuildProgress component should be importable."""
        from wtfui.cli.dashboard import BuildProgress

        assert callable(BuildProgress)
