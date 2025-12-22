from wtfui.core.protocol import RenderNode
from wtfui.core.style import Style
from wtfui.tui.renderer.renderer import ConsoleRenderer


class TestMouseState:
    """Test mouse state tracking in renderer."""

    def test_initial_mouse_position(self):
        """Renderer should start with mouse at (-1, -1)."""
        renderer = ConsoleRenderer(80, 24)

        assert renderer.mouse_x == -1
        assert renderer.mouse_y == -1

    def test_update_mouse(self):
        """update_mouse should update position and trigger repaint."""
        renderer = ConsoleRenderer(80, 24)

        changed = renderer.update_mouse(10, 5)

        assert renderer.mouse_x == 10
        assert renderer.mouse_y == 5
        assert changed is True  # Position changed

    def test_update_mouse_same_position(self):
        """update_mouse should return False if position unchanged."""
        renderer = ConsoleRenderer(80, 24)
        renderer.update_mouse(10, 5)

        changed = renderer.update_mouse(10, 5)

        assert changed is False  # No change


class TestHoverHitTesting:
    """Test hover style application via hit testing."""

    def test_hover_style_applied_when_mouse_over(self):
        """Element should use hover style when mouse is over it."""
        renderer = ConsoleRenderer(80, 24)
        renderer.update_mouse(2, 2)  # Mouse at (2, 2) - inside "Hello"

        # Create a node with hover style
        hover_style = Style(bg="blue-500")
        full_style = Style(color="white", bg="slate-800", hover=hover_style)

        node = RenderNode(
            tag="Text",
            element_id=1,
            text_content="Hello",
            props={
                "style": {
                    "left": 0,
                    "top": 2,
                    "width": 10,
                    "height": 1,
                    "_wtfui_style": full_style,  # Typed Style object
                }
            },
        )

        renderer.render_node_with_layout(node)

        # Check that cell at (2, 2) has blue background (hover applied)
        cell = renderer.back_buffer.get(2, 2)
        assert cell.bg == (59, 130, 246)  # blue-500

    def test_base_style_when_mouse_outside(self):
        """Element should use base style when mouse is outside."""
        renderer = ConsoleRenderer(80, 24)
        renderer.update_mouse(50, 10)  # Mouse far away

        hover_style = Style(bg="blue-500")
        full_style = Style(color="white", bg="slate-800", hover=hover_style)

        node = RenderNode(
            tag="Text",
            element_id=1,
            text_content="Hello",
            props={
                "style": {
                    "left": 0,
                    "top": 2,
                    "width": 10,
                    "height": 1,
                    "_wtfui_style": full_style,
                }
            },
        )

        renderer.render_node_with_layout(node)

        # Check that cell at (0, 2) has slate background (base, not hover)
        cell = renderer.back_buffer.get(0, 2)
        assert cell.bg == (30, 41, 59)  # slate-800


class TestInlineMode:
    """Tests for ConsoleRenderer inline mode."""

    def test_console_renderer_tracks_last_rendered_height(self):
        """Renderer should track height of previous frame."""
        renderer = ConsoleRenderer(80, 24)

        # Initially zero
        assert renderer.last_rendered_height == 0

        # After flush, should match current height
        renderer.flush()
        assert renderer.last_rendered_height == 24

    def test_console_renderer_flush_inline_emits_cursor_up(self):
        """Inline flush should emit cursor-up sequence to rewind."""
        renderer = ConsoleRenderer(80, 10)

        # First flush (no rewind needed)
        renderer.render_text_at(0, 0, "Hello")
        renderer.flush(inline=True)  # Discard output, just set last_rendered_height

        # Second flush should rewind
        renderer.render_text_at(0, 0, "World")
        output2 = renderer.flush(inline=True)

        # Should contain cursor up 10 lines: \x1b[10A
        assert "\x1b[10A" in output2, "Should emit cursor up sequence"
        # Should contain carriage return to go to start of line
        assert "\r" in output2, "Should emit carriage return"

    def test_console_renderer_flush_default_no_cursor_up(self):
        """Default flush (not inline) should NOT emit cursor-up."""
        renderer = ConsoleRenderer(80, 10)

        renderer.render_text_at(0, 0, "Hello")
        renderer.flush()  # First flush

        renderer.render_text_at(0, 0, "World")
        output = renderer.flush()  # Default, not inline

        # Should NOT contain cursor up
        assert "\x1b[10A" not in output, "Default flush should not emit cursor up"

    def test_console_renderer_resize_with_clear_false(self):
        """Resize with clear=False should not emit clear screen."""
        renderer = ConsoleRenderer(80, 24)

        # Default resize should emit clear screen
        output_with_clear = renderer.resize(100, 30)
        assert output_with_clear != "", "Default resize should emit clear sequence"

        # Resize with clear=False should return empty string
        output_no_clear = renderer.resize(80, 24, clear=False)
        assert output_no_clear == "", "Resize with clear=False should return empty string"

        # Verify buffers are resized
        assert renderer.width == 80
        assert renderer.height == 24


class TestCursorYTracking:
    """Tests for cursor Y position tracking (geometry fix)."""

    def test_renderer_initializes_last_cursor_y_to_zero(self):
        """New renderer should have last_cursor_y at 0."""
        renderer = ConsoleRenderer(80, 24)
        assert renderer.last_cursor_y == 0

    def test_flush_updates_last_cursor_y_with_cursor_target(self):
        """flush() should track cursor Y from cursor_target."""
        renderer = ConsoleRenderer(80, 10)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = (5, 3)  # Cursor at row 3
        renderer.flush(inline=True)

        assert renderer.last_cursor_y == 3

    def test_flush_updates_last_cursor_y_to_height_minus_one_without_target(self):
        """Without cursor_target, cursor parks at bottom (height - 1)."""
        renderer = ConsoleRenderer(80, 10)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = None
        renderer.flush(inline=True)

        assert renderer.last_cursor_y == 9  # height - 1

    def test_last_cursor_y_used_for_clear_sequence_not_height(self):
        """get_clear_sequence must use last_cursor_y, not height."""
        renderer = ConsoleRenderer(80, 10)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = (5, 2)  # Cursor at row 2
        renderer.flush(inline=True)

        clear_seq = renderer.get_clear_sequence()

        # Should move up 2 lines (cursor Y), NOT 10 (height)
        assert "\x1b[2A" in clear_seq
        assert "\x1b[10A" not in clear_seq


class TestGetClearSequence:
    """Tests for get_clear_sequence() method with cursor Y tracking."""

    def test_get_clear_sequence_returns_empty_when_no_previous_render(self):
        """No clear sequence needed if nothing was rendered yet."""
        renderer = ConsoleRenderer(80, 24)
        assert renderer.get_clear_sequence() == ""

    def test_get_clear_sequence_uses_cursor_y_not_height(self):
        """Clear sequence should move up by cursor Y position, not height."""
        renderer = ConsoleRenderer(80, 10)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = (0, 5)  # Cursor at row 5
        renderer.flush(inline=True)

        clear_seq = renderer.get_clear_sequence()

        # Move up 5 lines (where cursor is), clear down
        assert "\x1b[5A" in clear_seq
        assert "\x1b[J" in clear_seq
        # Should NOT use height
        assert "\x1b[10A" not in clear_seq

    def test_get_clear_sequence_when_cursor_at_bottom(self):
        """When cursor at bottom, should move up by height - 1."""
        renderer = ConsoleRenderer(80, 5)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = None  # Parks at bottom
        renderer.flush(inline=True)

        clear_seq = renderer.get_clear_sequence()

        # Cursor at row 4 (height - 1)
        assert "\x1b[4A" in clear_seq

    def test_get_clear_sequence_when_cursor_at_top(self):
        """When cursor at row 0, should move up 0 lines (just clear)."""
        renderer = ConsoleRenderer(80, 10)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = (0, 0)  # Cursor at row 0
        renderer.flush(inline=True)

        clear_seq = renderer.get_clear_sequence()

        # No cursor up needed, just clear
        assert "\x1b[0A" not in clear_seq or clear_seq == "\x1b[J"


class TestLazyFrameCache:
    """Tests for lazy frame caching (Sam Gross optimization)."""

    def test_renderer_initializes_cached_frame_to_none(self):
        """New renderer should have None cached frame (not computed yet)."""
        renderer = ConsoleRenderer(80, 24)
        assert renderer._cached_frame is None

    def test_flush_invalidates_cached_frame(self):
        """flush() should set _cached_frame to None (invalidate cache)."""
        renderer = ConsoleRenderer(10, 2)
        renderer.render_text_at(0, 0, "H")
        renderer._cached_frame = "old cached value"  # Pretend it was cached

        renderer.flush(inline=True)

        assert renderer._cached_frame is None  # Invalidated

    def test_repaint_computes_and_caches_frame_lazily(self):
        """repaint() should compute frame on first call, cache for subsequent."""
        renderer = ConsoleRenderer(10, 2)
        renderer.render_text_at(0, 0, "H")
        renderer.render_text_at(1, 0, "i")
        renderer.flush(inline=True)

        assert renderer._cached_frame is None  # Not computed yet

        output1 = renderer.repaint()

        assert renderer._cached_frame is not None  # Now cached
        assert "Hi" in output1

        output2 = renderer.repaint()

        assert output2 is output1  # Same cached string object

    def test_repaint_returns_empty_before_first_flush(self):
        """repaint() returns empty string before any flush."""
        renderer = ConsoleRenderer(10, 2)
        assert renderer.repaint() == ""

    def test_cached_frame_includes_cursor_position(self):
        """Cached frame should include cursor restoration."""
        from wtfui.tui.renderer import ansi

        renderer = ConsoleRenderer(80, 5)
        renderer.render_text_at(0, 0, "X")
        renderer.cursor_target = (10, 2)
        renderer.flush(inline=True)

        output = renderer.repaint()

        # Cached frame should end with cursor at (10, 2)
        assert ansi.cursor_move(10, 2) in output


class TestTextClipping:
    """Tests for text clipping to layout bounds."""

    def test_text_clipped_to_layout_width(self):
        """Text longer than layout width should be clipped."""
        renderer = ConsoleRenderer(80, 24)

        # Create a node with width=5 but text "Hello World" (11 chars)
        node = RenderNode(
            tag="Text",
            element_id=1,
            text_content="Hello World",
            props={
                "style": {
                    "left": 0,
                    "top": 0,
                    "width": 5,  # Only 5 chars should render
                    "height": 1,
                }
            },
        )

        renderer.render_node_with_layout(node)

        # First 5 chars should be written
        assert renderer.back_buffer.get(0, 0).char == "H"
        assert renderer.back_buffer.get(4, 0).char == "o"
        # Position 5 should NOT have " " from " World"
        # Position 6 should NOT have "W" from " World"
        assert renderer.back_buffer.get(5, 0).char == " ", (
            "Position 5 should be empty (default space)"
        )
        # Actually check position 6 has default char, not "W"
        cell = renderer.back_buffer.get(6, 0)
        assert cell.char == " ", f"Position 6 should be empty, got '{cell.char}'"

    def test_text_not_clipped_when_width_zero(self):
        """When width=0 (auto), text should not be clipped."""
        renderer = ConsoleRenderer(80, 24)

        node = RenderNode(
            tag="Text",
            element_id=1,
            text_content="Hello",
            props={
                "style": {
                    "left": 0,
                    "top": 0,
                    "width": 0,  # Auto width - no clipping
                    "height": 1,
                }
            },
        )

        renderer.render_node_with_layout(node)

        # All chars should be written
        assert renderer.back_buffer.get(0, 0).char == "H"
        assert renderer.back_buffer.get(4, 0).char == "o"


class TestLayoutResultDirectAccess:
    """Tests for renderer using LayoutResult directly."""

    def test_render_node_uses_layout_result_directly(self):
        """Verify renderer reads from layout field, not style strings."""
        from wtfui.tui.layout.node import LayoutResult

        renderer = ConsoleRenderer(width=80, height=24)

        # Create node with layout but no style strings
        node = RenderNode(
            tag="div",
            element_id=1,
            props={},
            layout=LayoutResult(x=5.0, y=3.0, width=10.0, height=2.0),
        )
        node.text_content = "Hello"

        renderer.render_node_with_layout(node)

        # Check that content was rendered at correct position
        cell = renderer.back_buffer.get(5, 3)
        assert cell.char == "H", f"Expected 'H' at (5,3), got '{cell.char}'"
