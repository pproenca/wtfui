"""Tests for Input element text editing."""


def test_input_has_cursor_position():
    """Input should track cursor position."""
    from wtfui.ui import Input

    inp = Input()
    assert hasattr(inp, "cursor_pos")
    assert inp.cursor_pos == 0


def test_input_has_text_value():
    """Input should track text value."""
    from wtfui.ui import Input

    inp = Input()
    assert hasattr(inp, "text_value")
    assert inp.text_value == ""


def test_input_syncs_with_bind_signal():
    """Input text_value should sync with bind Signal."""
    from wtfui.core.signal import Signal
    from wtfui.ui import Input

    text = Signal("hello")
    inp = Input(bind=text)

    assert inp.text_value == "hello"


def test_input_handle_keydown_inserts_char():
    """Input should insert character on keydown."""
    from wtfui.ui import Input

    inp = Input()
    inp.handle_keydown("a")

    assert inp.text_value == "a"
    assert inp.cursor_pos == 1


def test_input_handle_keydown_backspace():
    """Input should delete character on backspace."""
    from wtfui.ui import Input

    inp = Input()
    inp.text_value = "hello"
    inp.cursor_pos = 5

    inp.handle_keydown("backspace")

    assert inp.text_value == "hell"
    assert inp.cursor_pos == 4


# === Regression tests for Input value rendering ===


def test_input_render_node_includes_value_with_bind():
    """RenderTreeBuilder should include value attr for bound Input.

    Regression test: Input value should be rendered as HTML value attribute
    so the browser displays the correct value.
    """
    from wtfui.core.signal import Signal
    from wtfui.tui.builder import RenderTreeBuilder
    from wtfui.ui import Input

    text = Signal("hello world")
    inp = Input(bind=text)

    builder = RenderTreeBuilder()
    node = builder.build(inp)

    assert "value" in node.props, "value not in render node props"
    assert node.props["value"] == "hello world"


def test_input_render_node_includes_value_without_bind():
    """RenderTreeBuilder should include value attr for unbound Input.

    Regression test: Previously, Input without bind= would not have its
    text_value rendered, causing the displayed value to always show the
    placeholder instead of the actual typed value.
    """
    from wtfui.tui.builder import RenderTreeBuilder
    from wtfui.ui import Input

    inp = Input(placeholder="Type here")
    inp._text_value = "user typed this"  # Simulate server receiving input event

    builder = RenderTreeBuilder()
    node = builder.build(inp)

    assert "value" in node.props, "value not in render node props for unbound Input"
    assert node.props["value"] == "user typed this"


def test_input_on_change_updates_internal_state():
    """Input with on_change but no bind should still track text_value.

    This tests the Input element's internal state management when using
    only on_change callback without two-way binding.
    """
    from wtfui.ui import Input

    received_values = []

    def on_change(value: str) -> None:
        received_values.append(value)

    inp = Input(on_change=on_change)
    inp._text_value = "test value"  # Simulate what server does

    # Verify internal state is tracked
    assert inp.text_value == "test value"


def test_input_build_with_layout_includes_value():
    """build_with_layout should include value attr using text_value property.

    Regression test: build_with_layout was only checking bind.value, not the
    text_value property, causing inconsistency with build() which correctly
    uses text_value for both bound and unbound Inputs.
    """
    from wtfui.tui.builder import RenderTreeBuilder
    from wtfui.tui.layout.node import LayoutNode, LayoutResult
    from wtfui.tui.layout.style import FlexStyle
    from wtfui.ui import Input

    inp = Input(placeholder="100")
    inp._text_value = "200"  # Simulate server updating after user input

    # Create minimal layout node for build_with_layout
    layout_node = LayoutNode(style=FlexStyle())
    layout_node.layout = LayoutResult(x=0, y=0, width=100, height=30)

    builder = RenderTreeBuilder()
    node = builder.build_with_layout(inp, layout_node)

    assert "value" in node.props, "value not in render node props from build_with_layout"
    assert node.props["value"] == "200", f"Expected '200', got '{node.props.get('value')}'"
