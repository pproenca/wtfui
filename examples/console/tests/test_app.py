"""Tests for console app entry point."""


class TestApp:
    """Test component-based app entry."""

    def test_run_demo_function_exists(self) -> None:
        """run_demo function should exist."""
        from app import run_demo

        assert callable(run_demo)

    def test_uses_run_tui(self) -> None:
        """App should use run_tui for entry."""
        import inspect

        import app

        source = inspect.getsource(app)
        assert "run_tui" in source

    def test_uses_dashboard_component(self) -> None:
        """App should use Dashboard component."""
        import inspect

        import app

        source = inspect.getsource(app)
        assert "Dashboard" in source
