"""Tests for the console demo CLI command."""

from __future__ import annotations


def test_demo_module_exists():
    """Demo module can be imported."""
    from flow.cli import demo

    assert demo is not None


def test_demo_has_run_function():
    """Demo module has main entry point."""
    from flow.cli.demo import run_demo

    assert callable(run_demo)


def test_demo_command_registered():
    """Demo command is registered in CLI."""
    from flow.cli import cli

    # Check that 'demo' command exists in the CLI group
    assert "demo" in cli.commands


def test_app_state_creation():
    """AppState holds application state."""
    from flow.cli.demo import AppState

    state = AppState(width=80, height=24)
    assert state.width == 80
    assert state.height == 24
    assert state.running is True
    assert state.command_input == ""
    assert state.scroll_offset == 0


def test_app_state_focus_cycling():
    """AppState can cycle through focus areas."""
    from flow.cli.demo import AppState, FocusArea

    state = AppState(width=80, height=24)
    assert state.focus == FocusArea.PROCESSES

    state.cycle_focus()
    assert state.focus == FocusArea.COMMAND

    state.cycle_focus()
    assert state.focus == FocusArea.SIDEBAR

    state.cycle_focus()
    assert state.focus == FocusArea.PROCESSES


def test_app_state_command_editing():
    """AppState handles command input."""
    from flow.cli.demo import AppState

    state = AppState(width=80, height=24)

    state.type_char("k")
    state.type_char("i")
    state.type_char("l")
    state.type_char("l")
    assert state.command_input == "kill"

    state.backspace()
    assert state.command_input == "kil"

    state.clear_command()
    assert state.command_input == ""


def test_collect_system_stats():
    """collect_stats returns SystemStats with real data."""
    from flow.cli.demo import SystemStats, collect_stats

    stats = collect_stats()

    assert isinstance(stats, SystemStats)
    assert 0 <= stats.cpu_percent <= 100
    assert stats.memory_total_gb > 0
    assert stats.memory_used_gb >= 0
    assert stats.disk_total_gb > 0


def test_collect_processes():
    """collect_processes returns list of ProcessInfo."""
    from flow.cli.demo import ProcessInfo, collect_processes

    procs = collect_processes(limit=10)

    assert isinstance(procs, list)
    assert len(procs) <= 10
    if procs:  # At least one process should exist
        assert isinstance(procs[0], ProcessInfo)
        assert procs[0].pid >= 0  # PID 0 is valid (kernel_task on macOS)
        assert procs[0].name != ""


def test_collect_processes_sorted_by_cpu():
    """collect_processes sorts by CPU by default."""
    from flow.cli.demo import collect_processes

    procs = collect_processes(limit=20, sort_by="cpu")

    if len(procs) >= 2:
        # Should be sorted descending by CPU
        assert procs[0].cpu_percent >= procs[-1].cpu_percent


def test_build_layout_tree():
    """build_layout_tree creates LayoutNode hierarchy."""
    from flow.cli.demo import AppState, build_layout_tree
    from flow.layout.node import LayoutNode

    state = AppState(width=80, height=24)
    root = build_layout_tree(state)

    assert isinstance(root, LayoutNode)
    assert len(root.children) == 3  # header, main, footer


def test_layout_tree_has_correct_structure():
    """Layout tree matches dashboard structure."""
    from flow.cli.demo import AppState, build_layout_tree
    from flow.layout.style import FlexDirection

    state = AppState(width=80, height=24)
    root = build_layout_tree(state)

    # Root should be column
    assert root.style.flex_direction == FlexDirection.COLUMN

    # Main (second child) should be row with two children
    main = root.children[1]
    assert main.style.flex_direction == FlexDirection.ROW
    assert len(main.children) == 2  # sidebar, content


def test_layout_computes_positions():
    """Layout computation assigns positions to nodes."""
    from flow.cli.demo import AppState, build_layout_tree
    from flow.layout.compute import compute_layout
    from flow.layout.types import Size

    state = AppState(width=80, height=24)
    root = build_layout_tree(state)

    compute_layout(root, Size(80, 24))

    # Root should fill available space
    assert root.layout.width == 80
    assert root.layout.height == 24

    # Header should be at top
    header = root.children[0]
    assert header.layout.top == 0


def test_render_layout_to_buffer():
    """render_layout writes layout tree to ConsoleRenderer buffer."""
    from flow.cli.demo import AppState, build_layout_tree, render_layout
    from flow.layout.compute import compute_layout
    from flow.layout.types import Size
    from flow.renderer.console import ConsoleRenderer

    state = AppState(width=80, height=24)
    state.stats.cpu_percent = 45.0
    state.stats.memory_used_gb = 8.0
    state.stats.memory_total_gb = 16.0

    root = build_layout_tree(state)
    compute_layout(root, Size(80, 24))

    renderer = ConsoleRenderer(width=80, height=24)
    render_layout(renderer, root, state)

    output = renderer.flush()

    # Should contain dashboard elements
    assert "System Monitor" in output
    assert "CPU" in output


def test_parse_command_quit():
    """parse_command handles quit command."""
    from flow.cli.demo import AppState, CommandResult, parse_command

    state = AppState(width=80, height=24)
    result = parse_command("quit", state)

    assert result.action == "quit"
    assert state.running is False
    assert isinstance(result, CommandResult)


def test_parse_command_filter():
    """parse_command handles filter command."""
    from flow.cli.demo import AppState, parse_command

    state = AppState(width=80, height=24)
    result = parse_command("filter python", state)

    assert result.action == "filter"
    assert state.filter_text == "python"


def test_parse_command_kill():
    """parse_command handles kill command."""
    from flow.cli.demo import AppState, parse_command

    state = AppState(width=80, height=24)
    result = parse_command("kill 1234", state)

    assert result.action == "kill"
    assert result.target_pid == 1234


def test_parse_command_top():
    """parse_command handles top (sort by CPU) command."""
    from flow.cli.demo import AppState, parse_command

    state = AppState(width=80, height=24)
    state.sort_by = "mem"
    result = parse_command("top", state)

    assert result.action == "sort"
    assert state.sort_by == "cpu"


def test_parse_command_unknown():
    """parse_command handles unknown commands gracefully."""
    from flow.cli.demo import AppState, parse_command

    state = AppState(width=80, height=24)
    result = parse_command("unknown command", state)

    assert result.action == "error"
    assert "Unknown" in result.message


def test_handle_key_quit():
    """handle_key processes quit keys."""
    from flow.cli.demo import AppState, handle_key
    from flow.renderer.console.input import KeyEvent

    state = AppState(width=80, height=24)
    event = KeyEvent(key="q")

    handle_key(event, state)

    assert state.running is False


def test_handle_key_tab_cycles_focus():
    """handle_key Tab cycles focus areas."""
    from flow.cli.demo import AppState, FocusArea, handle_key
    from flow.renderer.console.input import KeyEvent

    state = AppState(width=80, height=24)
    assert state.focus == FocusArea.PROCESSES

    event = KeyEvent(key="tab")
    handle_key(event, state)

    assert state.focus == FocusArea.COMMAND


def test_handle_key_arrows_scroll():
    """handle_key arrows scroll process list."""
    from flow.cli.demo import AppState, FocusArea, ProcessInfo, handle_key
    from flow.renderer.console.input import KeyEvent

    state = AppState(width=80, height=24)
    state.focus = FocusArea.PROCESSES
    # Create fake processes for scrolling
    state.processes = [
        ProcessInfo(pid=i, name=f"proc{i}", cpu_percent=0, memory_mb=0) for i in range(100)
    ]

    event = KeyEvent(key="down")
    handle_key(event, state)

    assert state.scroll_offset == 1


def test_handle_key_typing_in_command():
    """handle_key types characters when command focused."""
    from flow.cli.demo import AppState, FocusArea, handle_key
    from flow.renderer.console.input import KeyEvent

    state = AppState(width=80, height=24)
    state.focus = FocusArea.COMMAND

    for char in "kill":
        event = KeyEvent(key=char)
        handle_key(event, state)

    assert state.command_input == "kill"


def test_handle_key_enter_executes_command():
    """handle_key Enter executes command."""
    from flow.cli.demo import AppState, FocusArea, handle_key
    from flow.renderer.console.input import KeyEvent

    state = AppState(width=80, height=24)
    state.focus = FocusArea.COMMAND
    state.command_input = "top"

    event = KeyEvent(key="enter")
    handle_key(event, state)

    assert state.sort_by == "cpu"
    assert state.command_input == ""  # Cleared after execution


def test_update_stats_modifies_state():
    """update_stats refreshes system statistics."""
    from flow.cli.demo import AppState, update_stats

    state = AppState(width=80, height=24)
    assert state.stats.cpu_percent == 0.0

    update_stats(state)

    # Stats should be populated (actual values depend on system)
    assert state.stats.memory_total_gb > 0
    assert len(state.processes) > 0
