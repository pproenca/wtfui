# tests/test_layout_reactive.py
from wtfui.core.signal import Signal
from wtfui.tui.layout.reactive import ReactiveLayoutNode
from wtfui.tui.layout.style import FlexDirection, FlexStyle


class TestReactiveLayout:
    def test_signal_style_change_marks_dirty(self):
        """Changing a Signal-bound style marks layout dirty."""
        width = Signal(100)

        node = ReactiveLayoutNode(style_signals={"width": width})

        # Initial state
        assert node.is_dirty()
        node.clear_dirty()
        assert not node.is_dirty()

        # Change signal
        width.value = 200
        assert node.is_dirty()

    def test_reactive_style_resolution(self):
        """Style resolves current Signal values."""
        grow = Signal(1.0)

        node = ReactiveLayoutNode(
            base_style=FlexStyle(flex_direction=FlexDirection.ROW),
            style_signals={"flex_grow": grow},
        )

        style = node.resolve_style()
        assert style.flex_grow == 1.0

        grow.value = 2.0
        style = node.resolve_style()
        assert style.flex_grow == 2.0

    def test_reactive_node_with_children(self):
        """ReactiveLayoutNode can have children."""
        parent = ReactiveLayoutNode()
        child = ReactiveLayoutNode()

        parent.add_child(child)

        assert len(parent.children) == 1
        assert child.parent is parent

    def test_child_dirty_propagates_to_parent(self):
        """When child becomes dirty, parent also becomes dirty."""
        width = Signal(100)
        parent = ReactiveLayoutNode()
        child = ReactiveLayoutNode(style_signals={"width": width})

        parent.add_child(child)
        parent.clear_dirty()
        child.clear_dirty()

        # Change child's signal
        width.value = 200

        assert child.is_dirty()
        assert parent.is_dirty()

    def test_to_layout_node_converts_tree(self):
        """to_layout_node creates static LayoutNode tree."""
        grow = Signal(1.0)
        parent = ReactiveLayoutNode(
            base_style=FlexStyle(flex_direction=FlexDirection.ROW),
        )
        child = ReactiveLayoutNode(style_signals={"flex_grow": grow})

        parent.add_child(child)

        layout_node = parent.to_layout_node()

        assert layout_node.style.flex_direction == FlexDirection.ROW
        assert len(layout_node.children) == 1
        assert layout_node.children[0].style.flex_grow == 1.0

    def test_dispose_unsubscribes_signals(self):
        """dispose() cleans up signal subscriptions."""
        width = Signal(100)
        node = ReactiveLayoutNode(style_signals={"width": width})

        node.clear_dirty()
        node.dispose()

        # After dispose, signal changes should not mark dirty
        width.value = 200
        assert not node.is_dirty()

    def test_multiple_signals(self):
        """Node can have multiple signal-bound properties."""
        width = Signal(100)
        height = Signal(50)
        grow = Signal(1.0)

        node = ReactiveLayoutNode(
            style_signals={
                "width": width,
                "height": height,
                "flex_grow": grow,
            }
        )

        node.clear_dirty()

        # Any signal change should mark dirty
        width.value = 200
        assert node.is_dirty()

        node.clear_dirty()
        height.value = 100
        assert node.is_dirty()

        node.clear_dirty()
        grow.value = 2.0
        assert node.is_dirty()

    def test_clear_dirty_recursive(self):
        """clear_dirty_recursive clears dirty flag for entire subtree."""
        width = Signal(100)
        parent = ReactiveLayoutNode()
        child = ReactiveLayoutNode(style_signals={"width": width})
        grandchild = ReactiveLayoutNode()

        parent.add_child(child)
        child.add_child(grandchild)

        # All nodes start dirty
        assert parent.is_dirty()
        assert child.is_dirty()
        assert grandchild.is_dirty()

        # Clear recursively
        parent.clear_dirty_recursive()

        assert not parent.is_dirty()
        assert not child.is_dirty()
        assert not grandchild.is_dirty()

        # Change signal - child and parent become dirty again
        width.value = 200
        assert parent.is_dirty()
        assert child.is_dirty()
        assert not grandchild.is_dirty()  # grandchild has no signal
