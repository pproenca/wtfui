"""Position-based tests for console dashboard.

These tests verify that elements are rendered at correct positions,
catching bugs like text overlap that substring-based tests miss.
"""

from unittest.mock import patch

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
async def test_sidebar_main_area_no_overlap():
    """Verify sidebar 'Resources' and main area 'Processes' don't overlap.

    The dashboard layout has:
    - Sidebar VStack with w=30 containing "Resources" label
    - Main VStack with flex_grow=1 containing "Processes" label

    "Resources" should be at x < 30 (in sidebar)
    "Processes" should be at x >= 30 (in main area)

    Bug symptom: Both render at similar x positions, creating "ResouProcesses"
    """
    from wtfui.tui.testing.driver import TUITestDriver

    with patch("components.dashboard.HAS_PSUTIL", False):
        from components.dashboard import Dashboard

        driver = TUITestDriver(Dashboard, width=80, height=24)
        await driver.start()

        buffer = driver.runtime.renderer.back_buffer
        width, height = 80, 24

        # Debug: dump buffer to see actual layout
        print("\n=== Buffer dump ===")
        print(dump_buffer(buffer, width, height))
        print("===================\n")

        # Find "Resources" position
        resources_pos = find_text_position(buffer, "Resources", width, height)
        assert resources_pos is not None, "Could not find 'Resources' in buffer"
        resources_x, resources_y = resources_pos

        # Find "Processes" position
        processes_pos = find_text_position(buffer, "Processes", width, height)
        assert processes_pos is not None, "Could not find 'Processes' in buffer"
        processes_x, processes_y = processes_pos

        print(f"Resources at ({resources_x}, {resources_y})")
        print(f"Processes at ({processes_x}, {processes_y})")

        # They should be on the same row (both are first labels in their sections)
        assert resources_y == processes_y, (
            f"Expected Resources and Processes on same row, got y={resources_y} and y={processes_y}"
        )

        # Resources must be in sidebar (x < 30)
        assert resources_x < 30, f"'Resources' at x={resources_x}, should be in sidebar (x < 30)"

        # Processes must be in main area (x >= 30)
        # With sidebar w=30 and main padding=2, Processes should be at x=32
        assert processes_x >= 30, (
            f"'Processes' at x={processes_x}, should be in main area (x >= 30). "
            f"This indicates sidebar width is not being respected."
        )

        # Sanity check: they shouldn't overlap
        resources_end = resources_x + len("Resources")
        assert resources_end <= processes_x, (
            f"Text overlap detected! 'Resources' ends at x={resources_end}, "
            f"but 'Processes' starts at x={processes_x}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("width", [80, 60, 50, 40])
async def test_sidebar_main_no_overlap_various_widths(width: int):
    """Test that sidebar and main area don't overlap at various terminal widths.

    The sidebar is w=30, so at narrow widths (< 60) there might be issues.
    """
    from wtfui.tui.testing.driver import TUITestDriver

    with patch("components.dashboard.HAS_PSUTIL", False):
        from components.dashboard import Dashboard

        height = 24
        driver = TUITestDriver(Dashboard, width=width, height=height)
        await driver.start()

        buffer = driver.runtime.renderer.back_buffer

        # Debug: dump buffer
        print(f"\n=== Buffer dump (width={width}) ===")
        print(dump_buffer(buffer, width, height))
        print("===================\n")

        # Find "Resources" position
        resources_pos = find_text_position(buffer, "Resou", width, height)
        # Find "Processes" position
        processes_pos = find_text_position(buffer, "Process", width, height)

        if resources_pos and processes_pos:
            resources_x, resources_y = resources_pos
            processes_x, processes_y = processes_pos

            print(
                f"At width={width}: Resources at ({resources_x}, {resources_y}), Processes at ({processes_x}, {processes_y})"
            )

            # Check they don't overlap
            if resources_y == processes_y:
                resources_end = resources_x + len("Resources")
                assert resources_end < processes_x, (
                    f"At width={width}: Text overlap! 'Resources' ends at x={resources_end}, "
                    f"'Processes' starts at x={processes_x}"
                )


@pytest.mark.asyncio
async def test_cpu_memory_labels_in_sidebar():
    """Verify CPU Usage and Memory Usage labels are in the sidebar area."""
    from wtfui.tui.testing.driver import TUITestDriver

    with patch("components.dashboard.HAS_PSUTIL", False):
        from components.dashboard import Dashboard

        driver = TUITestDriver(Dashboard, width=80, height=24)
        await driver.start()

        buffer = driver.runtime.renderer.back_buffer
        width, height = 80, 24

        # Find "CPU Usage" position
        cpu_pos = find_text_position(buffer, "CPU Usage", width, height)
        assert cpu_pos is not None, "Could not find 'CPU Usage' in buffer"
        cpu_x, cpu_y = cpu_pos

        # Find "Memory Usage" position
        memory_pos = find_text_position(buffer, "Memory Usage", width, height)
        assert memory_pos is not None, "Could not find 'Memory Usage' in buffer"
        memory_x, memory_y = memory_pos

        # Both should be in sidebar (x < 30)
        assert cpu_x < 30, f"'CPU Usage' at x={cpu_x}, should be in sidebar"
        assert memory_x < 30, f"'Memory Usage' at x={memory_x}, should be in sidebar"

        # Memory should be below CPU (not on same row)
        assert memory_y > cpu_y, (
            f"Expected Memory Usage below CPU Usage, got CPU at y={cpu_y}, Memory at y={memory_y}"
        )
