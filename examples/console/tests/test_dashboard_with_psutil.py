"""Test console dashboard with actual psutil data.

This test runs WITH psutil to see if dynamic process data causes layout issues.
"""

import pytest


def get_buffer_line(buffer, y: int, width: int) -> str:
    """Get a single line from the buffer as a string."""
    return "".join(buffer.get(x, y).char or " " for x in range(width))


def dump_buffer(buffer, width: int, height: int) -> str:
    """Dump entire buffer as string for debugging."""
    lines = []
    for y in range(height):
        line = get_buffer_line(buffer, y, width)
        lines.append(f"{y:2d}: {line.rstrip()}")
    return "\n".join(lines)


def find_text_position(buffer, text: str, width: int, height: int) -> tuple[int, int] | None:
    """Find (x, y) position of text in buffer."""
    for y in range(height):
        line = get_buffer_line(buffer, y, width)
        if text in line:
            return (line.find(text), y)
    return None


@pytest.mark.asyncio
async def test_dashboard_with_psutil_data():
    """Test dashboard WITH real psutil data to check for garbled output.

    This tests the full rendering path with dynamic process data.
    """
    # NO MOCK - run with real psutil
    from components.dashboard import HAS_PSUTIL, Dashboard

    from wtfui.tui.testing.driver import TUITestDriver

    if not HAS_PSUTIL:
        pytest.skip("psutil not available")

    width, height = 80, 24
    driver = TUITestDriver(Dashboard, width=width, height=height)
    await driver.start()

    buffer = driver.runtime.renderer.back_buffer

    # Debug: dump buffer
    print("\n=== Buffer dump WITH psutil ===")
    print(dump_buffer(buffer, width, height))
    print("===================\n")

    # Check for common corruption patterns
    for y in range(height):
        line = get_buffer_line(buffer, y, width)

        # Check for "ResouProcesses" overlap pattern
        if "ResouProcess" in line or "cesPro" in line:
            pytest.fail(f"Detected text overlap on row {y}:\n  {line!r}")

        # Check for garbled alphanumeric sequences (like "2223i22sc43com")
        # These indicate process data being written at wrong positions
        import re

        garbled_pattern = r"\d+[a-z]+\d+[a-z]+"
        if re.search(garbled_pattern, line.lower()):
            # Could be legitimate (like "com.apple.foo123")
            # But check if it's suspiciously long with no spaces
            words = line.split()
            for word in words:
                if len(word) > 30 and re.search(garbled_pattern, word.lower()):
                    pytest.fail(
                        f"Possible garbled output on row {y}:\n"
                        f"  {line!r}\n"
                        f"  Suspicious word: {word!r}"
                    )

    # Find key labels and verify positions
    resources_pos = find_text_position(buffer, "Resou", width, height)
    processes_pos = find_text_position(buffer, "Process", width, height)

    if resources_pos and processes_pos:
        resources_x, _ = resources_pos
        processes_x, _ = processes_pos
        print(f"Resources at x={resources_x}, Processes at x={processes_x}")

        # Sidebar w=30, so Processes should start at x >= 30
        assert processes_x >= 30, f"Processes at x={processes_x}, expected >= 30"

    # Check process list has header row
    pid_pos = find_text_position(buffer, "PID", width, height)
    assert pid_pos is not None, "PID header not found"
    pid_x, _pid_y = pid_pos
    assert pid_x >= 30, f"PID header at x={pid_x}, should be in main area (x >= 30)"


@pytest.mark.asyncio
async def test_dashboard_multiple_renders():
    """Test that multiple render cycles don't cause corruption.

    This catches issues where Signal updates cause partial re-renders
    that corrupt the buffer.
    """
    import asyncio

    from components.dashboard import HAS_PSUTIL, Dashboard

    from wtfui.tui.testing.driver import TUITestDriver

    if not HAS_PSUTIL:
        pytest.skip("psutil not available")

    width, height = 80, 24
    driver = TUITestDriver(Dashboard, width=width, height=height)
    await driver.start()

    # Allow multiple render cycles (Signal updates happen every 1s)
    # We'll trigger dirty flag multiple times
    for i in range(3):
        driver.runtime.is_dirty = True
        await asyncio.sleep(0.1)

        buffer = driver.runtime.renderer.back_buffer
        print(f"\n=== Render cycle {i + 1} ===")
        print(dump_buffer(buffer, width, height))

        # Check for corruption
        for y in range(height):
            line = get_buffer_line(buffer, y, width)
            if "ResouProcess" in line:
                pytest.fail(f"Overlap detected after render {i + 1} on row {y}")
