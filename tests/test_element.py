# tests/test_element.py
"""Tests for Element base class - the foundation of all UI nodes."""

from wtfui.core.context import get_current_parent
from wtfui.core.element import Element
from wtfui.core.signal import Signal
from wtfui.tui.layout.reactive import ReactiveLayoutNode


def test_element_has_tag_from_class_name():
    """Element tag defaults to class name."""
    el = Element()
    assert el.tag == "Element"


def test_element_stores_props():
    """Element stores arbitrary props."""
    el = Element(cls="container", id="main")
    assert el.props == {"cls": "container", "id": "main"}


def test_element_starts_with_no_children():
    """Element has empty children list."""
    el = Element()
    assert el.children == []


def test_element_context_manager_sets_parent():
    """Entering element sets it as current parent."""
    el = Element()
    assert get_current_parent() is None
    with el:
        assert get_current_parent() is el
    assert get_current_parent() is None


def test_element_nesting_builds_tree():
    """Nested context managers build parent-child relationships."""
    parent = Element()

    with parent:
        child = Element()  # Created INSIDE parent context

    assert child in parent.children
    assert child.parent is parent


def test_multiple_children():
    """Multiple children can be added to a parent."""
    parent = Element()

    with parent:
        child1 = Element()
        child2 = Element()

    assert parent.children == [child1, child2]


def test_element_auto_mounts_to_current_parent():
    """Element created inside a with block auto-attaches to parent."""
    parent = Element()

    with parent:
        child = Element()  # No 'with' block needed

    assert child in parent.children
    assert child.parent is parent


def test_element_detached_when_no_parent():
    """Element created outside any with block is detached."""
    el = Element()

    assert el.parent is None
    assert el.children == []


def test_auto_mount_multiple_children():
    """Multiple elements auto-mount in creation order."""
    parent = Element()

    with parent:
        child1 = Element()
        child2 = Element()
        child3 = Element()

    assert parent.children == [child1, child2, child3]
    assert all(c.parent is parent for c in parent.children)


def test_auto_mount_mixed_with_context_manager():
    """Auto-mount works alongside traditional with blocks."""
    parent = Element()

    with parent:
        leaf1 = Element()  # Auto-mounted
        with Element() as container:  # Traditional with block
            nested_leaf = Element()  # Auto-mounted to container
        leaf2 = Element()  # Auto-mounted to parent

    assert parent.children == [leaf1, container, leaf2]
    assert container.children == [nested_leaf]
    assert nested_leaf.parent is container


def test_layout_formatting_handles_float_precision():
    """Layout values are passed as raw floats in LayoutResult.

    Renderers are responsible for formatting to pixels/strings.
    RenderTreeBuilder passes the LayoutResult directly.
    """
    from wtfui.tui.builder import RenderTreeBuilder
    from wtfui.tui.layout.node import LayoutNode, LayoutResult
    from wtfui.tui.layout.style import FlexStyle

    elem = Element()
    layout = LayoutNode(style=FlexStyle())
    # Simulate floating point precision issues
    layout.layout = LayoutResult(x=10.0000001, y=20.9999999, width=100.5, height=50.0)

    render_node = RenderTreeBuilder().build_with_layout(elem, layout)

    # Layout should be passed directly as LayoutResult object
    assert render_node.layout is not None
    assert render_node.layout.x == 10.0000001
    assert render_node.layout.y == 20.9999999
    assert render_node.layout.width == 100.5
    assert render_node.layout.height == 50.0

    # Style dict should NOT contain layout strings
    style = render_node.props.get("style", {})
    assert "left" not in style
    assert "top" not in style
    assert "width" not in style
    assert "height" not in style


def test_element_to_render_node_preserves_style():
    """to_render_node should include _wtfui_style in props."""
    from wtfui.core.style import Style
    from wtfui.tui.builder import RenderTreeBuilder

    style = Style(color="white", hover=Style(color="blue-500"))

    # Create element with style
    elem = Element(style=style)

    node = RenderTreeBuilder().build(elem)

    # Style should be in props as _wtfui_style
    assert "style" in node.props
    assert "_wtfui_style" in node.props["style"]
    assert node.props["style"]["_wtfui_style"].hover is not None
    assert node.props["style"]["_wtfui_style"].color == "white"


class TestElementReactiveLayout:
    def test_to_reactive_layout_node_basic(self):
        """Element converts to ReactiveLayoutNode tree."""
        from wtfui.tui.adapter import ReactiveLayoutAdapter
        from wtfui.ui.elements import Div

        with Div() as parent:
            Div()
            Div()

        node = ReactiveLayoutAdapter().to_reactive_layout_node(parent)

        assert isinstance(node, ReactiveLayoutNode)
        assert len(node.children) == 2
        assert all(isinstance(c, ReactiveLayoutNode) for c in node.children)

    def test_to_reactive_layout_node_with_signal_width(self):
        """Signal-bound props create style_signals in ReactiveLayoutNode."""
        from wtfui.tui.adapter import ReactiveLayoutAdapter
        from wtfui.ui.elements import Div

        width = Signal(100)
        elem = Div(width=width)

        node = ReactiveLayoutAdapter().to_reactive_layout_node(elem)

        assert "width" in node.style_signals
        assert node.style_signals["width"] is width
        assert node.resolve_style().width.value == 100.0

    def test_to_reactive_layout_node_with_signal_height(self):
        """Signal height creates style_signal."""
        from wtfui.tui.adapter import ReactiveLayoutAdapter
        from wtfui.ui.elements import Div

        height = Signal(50)
        elem = Div(height=height)

        node = ReactiveLayoutAdapter().to_reactive_layout_node(elem)

        assert "height" in node.style_signals
        assert node.resolve_style().height.value == 50.0

    def test_to_reactive_layout_node_static_props(self):
        """Static props go to base_style, not style_signals."""
        from wtfui.tui.adapter import ReactiveLayoutAdapter
        from wtfui.ui.elements import Div

        elem = Div(width=100, height=50)

        node = ReactiveLayoutAdapter().to_reactive_layout_node(elem)

        assert len(node.style_signals) == 0
        assert node.base_style.width.value == 100.0
        assert node.base_style.height.value == 50.0


def test_invalidate_layout_notifies_runtime_when_present():
    """Element.invalidate_layout should set runtime.needs_rebuild when runtime is active."""
    from unittest.mock import Mock

    from wtfui.core.context import reset_runtime, set_current_runtime

    # Create mock runtime with needs_rebuild and is_dirty attributes
    mock_runtime = Mock()
    mock_runtime.needs_rebuild = False
    mock_runtime.is_dirty = False

    # Set runtime in context
    token = set_current_runtime(mock_runtime)
    try:
        element = Element()
        element.invalidate_layout()

        # Runtime should be notified
        assert mock_runtime.needs_rebuild is True
        assert mock_runtime.is_dirty is True
    finally:
        reset_runtime(token)


def test_invalidate_layout_works_without_runtime():
    """Element.invalidate_layout should not crash when no runtime is active."""
    from wtfui.core.context import reset_runtime, set_current_runtime

    # Ensure no runtime is set
    token = set_current_runtime(None)
    try:
        element = Element()
        # Should not raise
        element.invalidate_layout()
        # Just verify it doesn't crash - layout caching is now handled externally
    finally:
        reset_runtime(token)


def test_to_render_node_with_layout_passes_layout_directly():
    """Verify layout coordinates are passed as LayoutResult, not strings."""
    from wtfui.tui.builder import RenderTreeBuilder
    from wtfui.tui.layout.node import LayoutNode, LayoutResult
    from wtfui.tui.layout.style import FlexStyle

    elem = Element(tag="div")

    layout_node = LayoutNode(style=FlexStyle())
    layout_node.layout = LayoutResult(x=10.5, y=20.5, width=100.0, height=50.0)

    render_node = RenderTreeBuilder().build_with_layout(elem, layout_node)

    # Layout should be passed directly
    assert render_node.layout is not None
    assert render_node.layout.x == 10.5
    assert render_node.layout.y == 20.5

    # Style dict should NOT contain string coordinates
    style = render_node.props.get("style", {})
    assert "left" not in style or not isinstance(style.get("left"), str)
    assert "top" not in style or not isinstance(style.get("top"), str)
