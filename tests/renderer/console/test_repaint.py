# tests/renderer/console/test_repaint.py
"""Tests for repaint functionality preserving styles.

These tests verify that _compute_full_frame() includes ANSI color codes
in the output, not just raw characters.
"""

from wtfui.tui.renderer.renderer import ConsoleRenderer


class TestRepaintStyles:
    """Test that repaint output includes styling information."""

    def test_repaint_preserves_foreground_color(self):
        """Repaint should include foreground color ANSI codes."""
        renderer = ConsoleRenderer(80, 24)

        # Write red text directly to back buffer
        renderer.back_buffer.write_text(0, 0, "Hello", fg=(255, 0, 0))
        renderer.flush()

        # Get repaint output
        repaint = renderer.repaint()

        # Should contain ANSI foreground color code for red
        # Format: ESC[38;2;R;G;Bm
        assert "\x1b[38;2;255;0;0m" in repaint, (
            f"Repaint should contain red foreground code, got: {repaint!r}"
        )

    def test_repaint_preserves_background_color(self):
        """Repaint should include background color ANSI codes."""
        renderer = ConsoleRenderer(80, 24)

        # Write text with blue background
        renderer.back_buffer.write_text(0, 0, "World", bg=(0, 0, 255))
        renderer.flush()

        repaint = renderer.repaint()

        # Should contain ANSI background color code for blue
        # Format: ESC[48;2;R;G;Bm
        assert "\x1b[48;2;0;0;255m" in repaint, (
            f"Repaint should contain blue background code, got: {repaint!r}"
        )

    def test_repaint_preserves_bold(self):
        """Repaint should include bold ANSI codes."""
        renderer = ConsoleRenderer(80, 24)

        # Write bold text using Cell directly
        from wtfui.tui.renderer.cell import Cell

        renderer.back_buffer.set(0, 0, Cell(char="B", bold=True))
        renderer.flush()

        repaint = renderer.repaint()

        # Should contain ANSI bold code: ESC[1m
        assert "\x1b[1m" in repaint, f"Repaint should contain bold code, got: {repaint!r}"

    def test_repaint_preserves_multiple_styles(self):
        """Repaint should handle cells with multiple style attributes."""
        renderer = ConsoleRenderer(80, 24)

        from wtfui.tui.renderer.cell import Cell

        # Write cell with fg, bg, and bold
        renderer.back_buffer.set(
            0, 0, Cell(char="X", fg=(255, 255, 0), bg=(128, 0, 128), bold=True)
        )
        renderer.flush()

        repaint = renderer.repaint()

        # Should contain all style codes
        assert "\x1b[38;2;255;255;0m" in repaint, "Missing yellow foreground"
        assert "\x1b[48;2;128;0;128m" in repaint, "Missing purple background"
        assert "\x1b[1m" in repaint, "Missing bold"

    def test_repaint_resets_styles_at_end(self):
        """Repaint should reset styles at the end to avoid terminal artifacts."""
        renderer = ConsoleRenderer(80, 24)

        renderer.back_buffer.write_text(0, 0, "Test", fg=(255, 0, 0))
        renderer.flush()

        repaint = renderer.repaint()

        # Should end with reset sequence: ESC[0m
        assert "\x1b[0m" in repaint, f"Repaint should contain reset code, got: {repaint!r}"

    def test_repaint_empty_buffer_returns_empty(self):
        """Repaint of empty renderer should return empty string."""
        renderer = ConsoleRenderer(80, 24)

        # Don't write anything, don't flush
        repaint = renderer.repaint()

        assert repaint == "", f"Empty repaint should be empty, got: {repaint!r}"

    def test_repaint_caches_result(self):
        """Repaint should cache result for efficiency."""
        renderer = ConsoleRenderer(80, 24)

        renderer.back_buffer.write_text(0, 0, "Cached", fg=(0, 255, 0))
        renderer.flush()

        # First call computes
        repaint1 = renderer.repaint()
        # Second call returns cached
        repaint2 = renderer.repaint()

        assert repaint1 == repaint2, "Cached repaint should match"
        assert repaint1 is repaint2, "Should return same cached object"

    def test_repaint_handles_style_changes_between_cells(self):
        """Repaint should correctly handle style transitions between cells."""
        renderer = ConsoleRenderer(80, 24)

        # Write red then green adjacent cells
        from wtfui.tui.renderer.cell import Cell

        renderer.back_buffer.set(0, 0, Cell(char="R", fg=(255, 0, 0)))
        renderer.back_buffer.set(1, 0, Cell(char="G", fg=(0, 255, 0)))
        renderer.flush()

        repaint = renderer.repaint()

        # Should contain both colors
        assert "\x1b[38;2;255;0;0m" in repaint, "Missing red"
        assert "\x1b[38;2;0;255;0m" in repaint, "Missing green"
        # And the actual characters
        assert "R" in repaint
        assert "G" in repaint
