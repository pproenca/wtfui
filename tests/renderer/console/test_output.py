"""Tests for output interception (OutputRedirector, OutputProxy)."""

from __future__ import annotations

import io
import sys
import threading
from threading import RLock
from unittest.mock import MagicMock


class TestOutputProxy:
    """Tests for OutputProxy class."""

    def test_output_proxy_write_clears_logs_and_repaints(self):
        """OutputProxy should clear TUI, write log, then repaint TUI."""
        from wtfui.tui.renderer.output import OutputProxy

        # Mock renderer
        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = "\x1b[5A\x1b[J"
        mock_renderer.repaint.return_value = "[REPAINTED]"

        captured = io.StringIO()
        lock = RLock()

        proxy = OutputProxy(captured, mock_renderer, lock)
        proxy.write("Log message")
        proxy.flush()  # Force immediate flush

        output = captured.getvalue()

        # Order: clear -> log -> newline -> repaint
        assert output.index("\x1b[5A\x1b[J") < output.index("Log message")
        assert output.index("Log message") < output.index("[REPAINTED]")
        mock_renderer.repaint.assert_called_once()

    def test_output_proxy_adds_newline_if_missing(self):
        """Log messages without trailing newline should get one added."""
        from wtfui.tui.renderer.output import OutputProxy

        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = ""
        mock_renderer.repaint.return_value = ""

        captured = io.StringIO()
        lock = RLock()

        proxy = OutputProxy(captured, mock_renderer, lock)
        proxy.write("No newline")
        proxy.flush()  # Force immediate flush

        output = captured.getvalue()
        assert "No newline\n" in output

    def test_output_proxy_preserves_existing_newline(self):
        """Log messages with trailing newline should not get double newline."""
        from wtfui.tui.renderer.output import OutputProxy

        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = ""
        mock_renderer.repaint.return_value = ""

        captured = io.StringIO()
        lock = RLock()

        proxy = OutputProxy(captured, mock_renderer, lock)
        proxy.write("Has newline\n")
        proxy.flush()  # Force immediate flush

        output = captured.getvalue()
        assert "Has newline\n" in output
        assert "Has newline\n\n" not in output

    def test_output_proxy_write_empty_string_returns_zero(self):
        """Empty writes should return 0 without side effects."""
        from wtfui.tui.renderer.output import OutputProxy

        mock_renderer = MagicMock()
        captured = io.StringIO()
        lock = RLock()

        proxy = OutputProxy(captured, mock_renderer, lock)
        result = proxy.write("")

        assert result == 0
        mock_renderer.get_clear_sequence.assert_not_called()
        mock_renderer.repaint.assert_not_called()

    def test_output_proxy_flush_delegates_to_original(self):
        """flush() should flush buffered content to original stream."""
        from wtfui.tui.renderer.output import OutputProxy

        mock_original = MagicMock()
        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = ""
        mock_renderer.repaint.return_value = ""
        lock = RLock()

        proxy = OutputProxy(mock_original, mock_renderer, lock)
        proxy.write("test")
        proxy.flush()

        # Flush should have been called at least once (in _flush_buffer)
        assert mock_original.flush.called

    def test_output_proxy_isatty_delegates_to_original(self):
        """isatty() should delegate to original stream."""
        from wtfui.tui.renderer.output import OutputProxy

        mock_original = MagicMock()
        mock_original.isatty.return_value = True
        mock_renderer = MagicMock()
        lock = RLock()

        proxy = OutputProxy(mock_original, mock_renderer, lock)
        assert proxy.isatty() is True


class TestOutputRedirector:
    """Tests for OutputRedirector context manager."""

    def test_output_redirector_replaces_stdout_stderr_on_enter(self):
        """OutputRedirector should replace sys.stdout/stderr on entry."""
        from wtfui.tui.renderer.output import OutputProxy, OutputRedirector

        mock_renderer = MagicMock()
        lock = RLock()

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        manager = OutputRedirector(mock_renderer, lock)
        manager.__enter__()

        try:
            assert isinstance(sys.stdout, OutputProxy)
            assert isinstance(sys.stderr, OutputProxy)
            assert sys.stdout is not original_stdout
            assert sys.stderr is not original_stderr
        finally:
            manager.__exit__(None, None, None)

    def test_output_redirector_restores_stdout_stderr_on_exit(self):
        """OutputRedirector should restore original streams on exit."""
        from wtfui.tui.renderer.output import OutputRedirector

        mock_renderer = MagicMock()
        lock = RLock()

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with OutputRedirector(mock_renderer, lock):
            pass  # Just enter and exit

        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr

    def test_output_redirector_print_triggers_clear_and_repaint(self):
        """print() inside OutputRedirector should clear TUI, print, and repaint."""
        from wtfui.tui.renderer.output import OutputRedirector

        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = "[CLEAR]"
        mock_renderer.repaint.return_value = "[REPAINT]"

        lock = RLock()
        captured = io.StringIO()

        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            with OutputRedirector(mock_renderer, lock):
                print("Test message")
                # print() calls flush(), so output should be immediate

            output = captured.getvalue()
            assert "[CLEAR]" in output
            assert "Test message" in output
            assert "[REPAINT]" in output
        finally:
            sys.stdout = original_stdout

    def test_output_redirector_flushes_on_exception(self):
        """OutputRedirector should flush buffered content even when exception occurs."""
        from wtfui.tui.renderer.output import OutputRedirector

        mock_renderer = MagicMock()
        mock_renderer.get_clear_sequence.return_value = "[CLEAR]"
        mock_renderer.repaint.return_value = "[REPAINT]"

        lock = RLock()
        captured = io.StringIO()

        original_stdout = sys.stdout
        sys.stdout = captured

        try:
            with OutputRedirector(mock_renderer, lock):
                print("Before exception", end="")  # No newline, stays in buffer
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        finally:
            sys.stdout = original_stdout

        # Buffer should have been flushed on __exit__
        output = captured.getvalue()
        assert "Before exception" in output
        assert "[CLEAR]" in output
        assert "[REPAINT]" in output


class TestOutputProxyBatching:
    """Tests for debounced batching in OutputProxy."""

    def test_multiple_writes_batch_into_single_repaint(self):
        """Multiple rapid writes should trigger only one repaint."""
        from unittest.mock import patch

        from wtfui.tui.renderer.output import OutputProxy

        original = io.StringIO()
        renderer = MagicMock()
        renderer.get_clear_sequence.return_value = "[CLEAR]"
        renderer.repaint.return_value = "[REPAINT]"
        lock = threading.RLock()

        # Capture timer callbacks to invoke them directly
        timer_callback = None

        def mock_timer(delay, callback):
            nonlocal timer_callback
            timer_callback = callback
            mock = MagicMock()
            mock.daemon = True
            return mock

        with patch("threading.Timer", side_effect=mock_timer):
            proxy = OutputProxy(original, renderer, lock)

            # Write multiple times rapidly
            proxy.write("line1\n")
            proxy.write("line2\n")
            proxy.write("line3\n")

            # Force flush
            proxy.flush()

        # Should have batched: only 1 clear and 1 repaint
        # (after flush forces the batch)
        output = original.getvalue()

        # Count clear/repaint occurrences
        clear_count = output.count("[CLEAR]")
        repaint_count = output.count("[REPAINT]")

        # With batching, should be exactly 1 clear/repaint cycle
        assert clear_count == 1, f"Expected exactly 1 clear, got {clear_count}"
        assert repaint_count == 1, f"Expected exactly 1 repaint, got {repaint_count}"

    def test_flush_forces_immediate_output(self):
        """flush() should immediately output buffered content."""
        from wtfui.tui.renderer.output import OutputProxy

        original = io.StringIO()
        renderer = MagicMock()
        renderer.get_clear_sequence.return_value = ""
        renderer.repaint.return_value = ""
        lock = threading.RLock()

        proxy = OutputProxy(original, renderer, lock)

        proxy.write("test content")
        proxy.flush()

        assert "test content" in original.getvalue()

    def test_debounce_timer_flushes_buffer(self):
        """Debounce timer should flush accumulated content after delay."""
        from unittest.mock import patch

        from wtfui.tui.renderer.output import OutputProxy

        original = io.StringIO()
        renderer = MagicMock()
        renderer.get_clear_sequence.return_value = ""
        renderer.repaint.return_value = ""
        lock = threading.RLock()

        # Capture the timer callback so we can invoke it directly
        timer_callback = None

        def mock_timer(delay, callback):
            nonlocal timer_callback
            timer_callback = callback
            mock = MagicMock()
            mock.daemon = True
            return mock

        with patch("threading.Timer", side_effect=mock_timer):
            proxy = OutputProxy(original, renderer, lock)

            proxy.write("hello")
            proxy.write(" world\n")

            # Invoke the timer callback directly (simulates timer firing)
            assert timer_callback is not None
            timer_callback()

        assert "hello world" in original.getvalue()

    def test_concurrent_writes_from_multiple_threads(self):
        """Multiple threads writing concurrently should not corrupt output."""
        from wtfui.tui.renderer.output import OutputProxy

        original = io.StringIO()
        renderer = MagicMock()
        renderer.get_clear_sequence.return_value = ""
        renderer.repaint.return_value = ""
        lock = threading.RLock()

        proxy = OutputProxy(original, renderer, lock)
        errors = []

        def writer(thread_id: int, count: int):
            try:
                for i in range(count):
                    proxy.write(f"thread{thread_id}-msg{i}\n")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        proxy.flush()

        # No exceptions should have occurred
        assert not errors, f"Errors during concurrent writes: {errors}"

        # All messages should be present (order may vary)
        output = original.getvalue()
        for thread_id in range(5):
            for msg_id in range(10):
                assert f"thread{thread_id}-msg{msg_id}" in output

    def test_rapid_writes_cancel_and_reschedule_timer(self):
        """Rapid writes should cancel pending timer and reschedule."""
        from unittest.mock import patch

        from wtfui.tui.renderer.output import OutputProxy

        original = io.StringIO()
        renderer = MagicMock()
        renderer.get_clear_sequence.return_value = "[CLEAR]"
        renderer.repaint.return_value = "[REPAINT]"
        lock = threading.RLock()

        # Capture timer callbacks to invoke them directly
        timer_callback = None
        cancel_count = 0

        def mock_timer(delay, callback):
            nonlocal timer_callback, cancel_count
            timer_callback = callback
            mock = MagicMock()
            mock.daemon = True
            mock.cancel = MagicMock(side_effect=lambda: setattr(mock, "_cancelled", True))
            return mock

        with patch("threading.Timer", side_effect=mock_timer):
            proxy = OutputProxy(original, renderer, lock)

            # Write rapidly, each should cancel the previous timer
            for i in range(10):
                proxy.write(f"msg{i}\n")

            # Simulate the final timer firing
            if timer_callback:
                timer_callback()

        output = original.getvalue()

        # Should have batched all 10 messages into single cycle
        assert output.count("[CLEAR]") == 1
        assert output.count("[REPAINT]") == 1

        # All messages should be present
        for i in range(10):
            assert f"msg{i}" in output
