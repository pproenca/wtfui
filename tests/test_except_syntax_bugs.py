"""Tests for terminal.py exception handling on platforms without termios.

These tests verify that setup_raw_mode and restore_terminal gracefully handle
ImportError when termios is unavailable (e.g., on Windows).
"""

import builtins
import sys
from unittest.mock import MagicMock, patch


class TestTerminalWithoutTermios:
    """Test terminal.py functions when termios is unavailable."""

    def test_setup_raw_mode_handles_missing_termios(self):
        """setup_raw_mode should not crash when termios is unavailable.

        On platforms without termios (Windows), the function should
        gracefully handle ImportError without raising any exception.
        """
        import wtfui.tui.renderer.terminal as terminal_module

        # Reset state
        terminal_module._original_termios = None

        original_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "termios":
                raise ImportError("termios not available")
            return original_import(name, *args, **kwargs)

        # Clear cached termios
        for key in list(sys.modules.keys()):
            if "termios" in key:
                del sys.modules[key]

        # Create a mock stdin that claims to be a tty
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.fileno.return_value = 0

        builtins.__import__ = blocking_import
        try:
            with patch.object(sys, "stdin", mock_stdin):
                # This should NOT raise any exception
                terminal_module.setup_raw_mode()
        finally:
            builtins.__import__ = original_import
            terminal_module._original_termios = None

    def test_restore_terminal_handles_missing_termios(self):
        """restore_terminal should not crash when termios is unavailable."""
        import wtfui.tui.renderer.terminal as terminal_module

        original_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "termios":
                raise ImportError("termios not available")
            return original_import(name, *args, **kwargs)

        for key in list(sys.modules.keys()):
            if "termios" in key:
                del sys.modules[key]

        # Create a mock stdin that claims to be a tty
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.fileno.return_value = 0

        # Set _original_termios to trigger the restore path
        terminal_module._original_termios = [0] * 7

        builtins.__import__ = blocking_import
        try:
            with patch.object(sys, "stdin", mock_stdin):
                # This should NOT raise any exception
                terminal_module.restore_terminal()
        finally:
            builtins.__import__ = original_import
            terminal_module._original_termios = None
