"""Tests for run_tui public API."""

from unittest.mock import MagicMock, patch


def test_run_tui_accepts_inline_parameter():
    """run_tui should accept inline=True and pass it to TUIRuntime."""
    from wtfui.tui.renderer.runtime import run_tui

    def dummy_app():
        pass

    with patch("wtfui.tui.renderer.runtime.TUIRuntime") as mock_runtime:
        mock_instance = MagicMock()
        mock_runtime.return_value = mock_instance

        run_tui(dummy_app, inline=True)

        mock_runtime.assert_called_once()
        call_kwargs = mock_runtime.call_args.kwargs
        assert call_kwargs.get("inline") is True


def test_run_tui_inline_defaults_to_false():
    """run_tui should default inline=False."""
    from wtfui.tui.renderer.runtime import run_tui

    def dummy_app():
        pass

    with patch("wtfui.tui.renderer.runtime.TUIRuntime") as mock_runtime:
        mock_instance = MagicMock()
        mock_runtime.return_value = mock_instance

        run_tui(dummy_app)

        call_kwargs = mock_runtime.call_args.kwargs
        # inline should be False or not present (defaults to False in TUIRuntime)
        assert call_kwargs.get("inline", False) is False
