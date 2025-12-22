"""Tests for Element integration with ReactiveLayoutNode."""

from wtfui.core.element import Element
from wtfui.core.signal import Signal
from wtfui.tui.adapter import ReactiveLayoutAdapter
from wtfui.tui.layout.reactive import ReactiveLayoutNode


class TestElementReactiveLayout:
    """Element creates ReactiveLayoutNode when props contain Signals."""

    def test_signal_prop_creates_reactive_node(self):
        """Element with Signal prop creates ReactiveLayoutNode."""
        width = Signal(100)
        el = Element(tag="div", width=width)

        reactive_node = ReactiveLayoutAdapter().to_reactive_layout_node(el)

        assert isinstance(reactive_node, ReactiveLayoutNode)
        assert "width" in reactive_node.style_signals
        assert reactive_node.style_signals["width"] is width

    def test_static_props_in_base_style(self):
        """Non-Signal props go into base_style."""
        width = Signal(100)
        el = Element(tag="div", width=width, height=50)

        reactive_node = ReactiveLayoutAdapter().to_reactive_layout_node(el)

        assert reactive_node.base_style.height.value == 50.0
        assert "height" not in reactive_node.style_signals

    def test_children_converted_recursively(self):
        """Child elements converted to ReactiveLayoutNode children."""
        parent = Element(tag="div")
        child = Element(tag="span")
        parent.children.append(child)

        reactive_node = ReactiveLayoutAdapter().to_reactive_layout_node(parent)

        assert len(reactive_node.children) == 1
        assert isinstance(reactive_node.children[0], ReactiveLayoutNode)

    def test_no_signal_props_creates_static_node(self):
        """Element without Signal props can still create ReactiveLayoutNode."""
        el = Element(tag="div", width=100, height=50)

        reactive_node = ReactiveLayoutAdapter().to_reactive_layout_node(el)

        assert isinstance(reactive_node, ReactiveLayoutNode)
        assert reactive_node.base_style.width.value == 100.0
        assert reactive_node.base_style.height.value == 50.0
        assert len(reactive_node.style_signals) == 0
