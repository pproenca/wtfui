"""Test ReactiveLayoutAdapter converts Elements with Signal props."""

from wtfui.core.element import Element
from wtfui.core.signal import Signal


def test_reactive_adapter_import():
    """ReactiveLayoutAdapter should be importable from wtfui.tui."""
    from wtfui.tui import ReactiveLayoutAdapter

    assert ReactiveLayoutAdapter is not None


def test_reactive_adapter_converts_static_element():
    """ReactiveLayoutAdapter should convert Element without Signals."""
    from wtfui.tui import ReactiveLayoutAdapter

    elem = Element(width=100, height=50)
    adapter = ReactiveLayoutAdapter()
    node = adapter.to_reactive_layout_node(elem)

    assert node is not None
    assert node.base_style.width is not None


def test_reactive_adapter_tracks_signal_props():
    """ReactiveLayoutAdapter should bind Signal props for reactivity."""
    from wtfui.tui import ReactiveLayoutAdapter

    width_signal = Signal(100)
    elem = Element(width=width_signal, height=50)
    adapter = ReactiveLayoutAdapter()
    node = adapter.to_reactive_layout_node(elem)

    assert node is not None
    assert "width" in node.style_signals
    assert node.style_signals["width"] is width_signal
