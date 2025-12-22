# tests/test_element_render_node.py
"""Tests for RenderTreeBuilder with Tailwind conflict resolution and Input binding."""

from wtfui.core.element import Element
from wtfui.core.signal import Signal
from wtfui.tui.builder import RenderTreeBuilder
from wtfui.ui.elements import Input


class TestRenderNodeTailwindConflict:
    """Tailwind classes stripped when explicit props conflict."""

    def test_width_prop_strips_tailwind_width_class(self):
        """Explicit width prop removes w-* Tailwind classes."""
        el = Element(tag="div", class_="w-10 bg-blue-500", width=100)
        node = RenderTreeBuilder().build(el)

        # class_ should have w-10 stripped, bg-blue-500 preserved
        assert "w-10" not in node.props.get("class_", "")
        assert "bg-blue-500" in node.props.get("class_", "")

    def test_no_stripping_without_explicit_props(self):
        """Tailwind classes preserved when no explicit props conflict."""
        el = Element(tag="div", class_="w-10 h-10 bg-red-500")
        node = RenderTreeBuilder().build(el)

        # All classes preserved
        class_str = node.props.get("class_", "")
        assert "w-10" in class_str
        assert "h-10" in class_str
        assert "bg-red-500" in class_str

    def test_multiple_conflicts_stripped(self):
        """Multiple conflicting Tailwind classes stripped."""
        el = Element(
            tag="div",
            class_="w-full h-screen flex-row justify-center p-4",
            width=200,
            height=100,
            flex_direction="row",
            justify_content="center",
        )
        node = RenderTreeBuilder().build(el)

        class_str = node.props.get("class_", "")
        # Geometry classes stripped
        assert "w-full" not in class_str
        assert "h-screen" not in class_str
        assert "flex-row" not in class_str
        assert "justify-center" not in class_str
        # Non-geometry preserved
        assert "p-4" in class_str


class TestRenderNodeInputBinding:
    """Input elements with bind should render value attribute."""

    def test_input_with_bind_renders_value_attribute(self):
        """Input bind.value should be extracted and added as value prop.

        Regression test: Without this fix, Input elements with Signal binding
        would not render the value attribute in HTML, causing the browser to
        show stale values after re-renders.
        """
        bound_signal = Signal("test value")
        el = Input(bind=bound_signal, placeholder="Enter text")

        node = RenderTreeBuilder().build(el)

        # value prop should be extracted from bind.value
        assert "value" in node.props
        assert node.props["value"] == "test value"

    def test_input_without_bind_has_value_prop(self):
        """Input without bind should have value prop from text_value property.

        Even unbound Inputs need value rendered so that:
        1. Server-side updates to _text_value are reflected in HTML
        2. The displayed value matches the internal state
        """
        el = Input(placeholder="Enter text")

        node = RenderTreeBuilder().build(el)

        # value prop should be added from text_value (empty string for fresh Input)
        assert "value" in node.props
        assert node.props["value"] == ""

    def test_input_bind_value_updates_on_signal_change(self):
        """Verify bind.value reflects current signal value at render time."""
        bound_signal = Signal("initial")
        el = Input(bind=bound_signal)

        # Change signal value before building
        bound_signal.value = "updated"

        node = RenderTreeBuilder().build(el)

        # Should reflect current signal value
        assert node.props["value"] == "updated"
