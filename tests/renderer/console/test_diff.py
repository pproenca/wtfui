# tests/test_console_diff.py
"""Tests for differential buffer painting."""

from wtfui.tui.renderer.buffer import Buffer
from wtfui.tui.renderer.cell import Cell
from wtfui.tui.renderer.diff import diff_buffers


def test_diff_empty_buffers():
    """Two empty buffers produce no diff."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    result = diff_buffers(buf_a, buf_b)

    assert result.changes == []
    assert result.ansi_output == ""


def test_diff_single_change():
    """Single cell change produces minimal output."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(3, 2, Cell(char="X"))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
    assert result.changes[0] == (3, 2)
    assert "X" in result.ansi_output


def test_diff_multiple_changes():
    """Multiple changes are batched efficiently."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(0, 0, Cell(char="A"))
    buf_b.set(1, 0, Cell(char="B"))
    buf_b.set(2, 0, Cell(char="C"))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 3
    # Adjacent cells should ideally be written together
    assert "ABC" in result.ansi_output or all(c in result.ansi_output for c in "ABC")


def test_diff_with_colors():
    """Color changes are included in output."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)
    buf_b.set(0, 0, Cell(char="X", fg=(255, 0, 0)))

    result = diff_buffers(buf_a, buf_b)

    # Should include RGB color escape sequence
    assert "38;2;255;0;0" in result.ansi_output


def test_diff_identical_cells_no_change():
    """Identical cells produce no diff."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    cell = Cell(char="Y", fg=(0, 255, 0))
    buf_a.set(5, 3, cell)
    buf_b.set(5, 3, Cell(char="Y", fg=(0, 255, 0)))  # Same content

    result = diff_buffers(buf_a, buf_b)

    assert (5, 3) not in result.changes


def test_diff_respects_style_changes():
    """Style-only changes (bold, dim) are detected."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    buf_a.set(0, 0, Cell(char="X", bold=False))
    buf_b.set(0, 0, Cell(char="X", bold=True))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1


def test_diff_italic_style():
    """Italic style changes are detected and emitted."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    buf_b.set(0, 0, Cell(char="I", italic=True))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
    # ANSI italic is ESC[3m
    assert "\x1b[3m" in result.ansi_output


def test_diff_underline_style():
    """Underline style changes are detected and emitted."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    buf_b.set(0, 0, Cell(char="U", underline=True))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
    # ANSI underline is ESC[4m
    assert "\x1b[4m" in result.ansi_output


def test_diff_italic_to_non_italic_resets():
    """Transitioning from italic to non-italic requires reset."""
    buf_a = Buffer(width=10, height=5)
    buf_b = Buffer(width=10, height=5)

    buf_a.set(0, 0, Cell(char="A", italic=True))
    buf_b.set(0, 0, Cell(char="A", italic=False))

    result = diff_buffers(buf_a, buf_b)

    assert len(result.changes) == 1
    # Should include reset sequence ESC[0m
    assert "\x1b[0m" in result.ansi_output


def test_diff_buffers_performance_local_lookup():
    """diff_buffers should use local variable lookup for performance."""
    import time

    # Create large buffers (100x50 = 5000 cells)
    width, height = 100, 50
    old_buffer = Buffer(width, height)
    new_buffer = Buffer(width, height)

    # Fill with different content to force full diff
    for y in range(height):
        for x in range(width):
            old_buffer.set(x, y, Cell(char="A"))
            new_buffer.set(x, y, Cell(char="B"))

    # Warm up
    diff_buffers(old_buffer, new_buffer)

    # Time 100 iterations
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        diff_buffers(old_buffer, new_buffer)
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000

    # Should complete each diff in under 10ms for 5000 cells
    # This is a regression test - if we regress, the optimization was lost
    assert avg_ms < 10, f"diff_buffers too slow: {avg_ms:.2f}ms per call (expected <10ms)"


def test_diff_buffers_handles_large_terminal_efficiently():
    """diff_buffers should handle 200x60 terminal in under 10ms.

    This tests the O(W*H) optimization using enumerate() instead of nested range().
    """
    import time

    width, height = 200, 60  # ~12,000 cells

    old_buffer = Buffer(width, height)
    new_buffer = Buffer(width, height)

    # Write some text to create differences
    new_buffer.write_text(0, 0, "Hello World")
    new_buffer.write_text(50, 30, "Middle text")
    new_buffer.write_text(150, 55, "Bottom right")

    # Warm up
    diff_buffers(old_buffer, new_buffer)

    # Benchmark
    start = time.perf_counter()
    for _ in range(10):
        result = diff_buffers(old_buffer, new_buffer)
    elapsed = (time.perf_counter() - start) / 10

    # Should complete in under 10ms per call
    assert elapsed < 0.010, f"diff_buffers took {elapsed * 1000:.2f}ms, expected <10ms"

    # Verify correctness
    assert len(result.changes) > 0
    assert len(result.ansi_output) > 0


def test_diff_no_divmod_in_hot_loop():
    """Verify diff uses nested loops instead of divmod for coordinates."""
    import dis

    from wtfui.tui.renderer.diff import diff_buffers

    # Get bytecode of diff_buffers
    bytecode = dis.Bytecode(diff_buffers)
    instructions = list(bytecode)

    # Check that divmod is not called in the function
    divmod_calls = [i for i in instructions if "divmod" in str(i)]
    assert len(divmod_calls) == 0, f"diff_buffers should not use divmod, found: {divmod_calls}"
