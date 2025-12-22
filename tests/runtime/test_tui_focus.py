"""Tests for TUIRuntime focus management."""

import asyncio


def test_tui_runtime_has_focused_element_id():
    """TUIRuntime should track focused element ID."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)
    assert hasattr(runtime, "focused_element_id")
    assert runtime.focused_element_id is None


def test_tui_runtime_set_focus():
    """TUIRuntime should allow setting focus to an element."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)
    runtime.set_focus(12345)
    assert runtime.focused_element_id == 12345


def test_tui_runtime_clear_focus():
    """TUIRuntime should allow clearing focus."""
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)
    runtime.set_focus(12345)
    runtime.set_focus(None)
    assert runtime.focused_element_id is None


def test_tui_runtime_routes_key_to_focused_element():
    """KeyEvent should be dispatched to focused element's keydown handler."""
    from wtfui.tui.renderer.input import KeyEvent
    from wtfui.tui.runtime import TUIRuntime

    received_keys = []

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)

    # Create a mock element with on_keydown handler
    mock_element = type(
        "MockElement",
        (),
        {"props": {"on_keydown": lambda key: received_keys.append(key)}},
    )()
    runtime._registry._elements[12345] = mock_element
    runtime.focused_element_id = 12345

    # Simulate key event
    event = KeyEvent(key="a", ctrl=False, alt=False, shift=False)
    asyncio.run(runtime._handle_event(event))

    assert "a" in received_keys, "Key should be dispatched to focused element"


def test_tui_runtime_focus_on_click():
    """Clicking a focusable element should set focus."""
    from unittest.mock import MagicMock

    from wtfui.tui.layout.node import LayoutNode, LayoutResult
    from wtfui.tui.renderer.input import MouseEvent
    from wtfui.tui.runtime import TUIRuntime

    def dummy_app():
        pass

    runtime = TUIRuntime(dummy_app)

    # Mock a focusable element
    mock_element = MagicMock()
    mock_element.focusable = True
    mock_element.props = {}

    # Mock layout node with hit test
    mock_layout = MagicMock(spec=LayoutNode)
    mock_layout.layout = LayoutResult(x=0, y=0, width=10, height=1)
    mock_layout.hit_test = MagicMock(return_value=mock_layout)

    runtime.layout_root = mock_layout
    runtime._layout_to_element[id(mock_layout)] = mock_element
    runtime._registry._elements[id(mock_element)] = mock_element

    # Simulate click (button=0 is left click)
    event = MouseEvent(x=5, y=0, button=0, pressed=True)
    asyncio.run(runtime._handle_event(event))

    assert runtime.focused_element_id == id(mock_element), "Click should focus the element"
