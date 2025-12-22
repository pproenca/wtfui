"""Tests for snapshot visual capture."""

from wtfui.tui.renderer import ConsoleRenderer


class TestSnapshot:
    """Test snapshot() for capturing rendered output."""

    def test_snapshot_returns_string_representation(self):
        """snapshot() should return string of buffer contents."""
        from wtfui.tui.testing.snapshot import snapshot

        renderer = ConsoleRenderer(width=20, height=5)
        renderer.render_text_at(0, 0, "Hello")
        renderer.flush()  # Swap buffers so content is in front_buffer

        result = snapshot(renderer)

        assert isinstance(result, str)
        assert "Hello" in result

    def test_snapshot_preserves_layout(self):
        """snapshot() should preserve position of rendered text."""
        from wtfui.tui.testing.snapshot import snapshot

        renderer = ConsoleRenderer(width=20, height=5)
        renderer.render_text_at(5, 2, "Center")
        renderer.flush()  # Swap buffers so content is in front_buffer

        result = snapshot(renderer)
        lines = result.split("\n")

        # Line 2 should have "Center" at position 5
        assert len(lines) > 2
        assert "Center" in lines[2]

    def test_snapshot_from_front_buffer(self):
        """snapshot() reads from front_buffer after flush."""
        from wtfui.tui.testing.snapshot import snapshot

        renderer = ConsoleRenderer(width=20, height=3)
        renderer.render_text_at(0, 0, "Line 1")
        renderer.flush()  # Swap buffers

        result = snapshot(renderer)

        assert "Line 1" in result
