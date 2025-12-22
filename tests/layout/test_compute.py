# tests/test_layout_compute.py
from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.node import LayoutNode
from wtfui.tui.layout.style import FlexDirection, FlexStyle, JustifyContent
from wtfui.tui.layout.types import Dimension, Size


class TestComputeLayout:
    def test_single_node_fixed_size(self):
        """Single node with fixed dimensions."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )

        compute_layout(node, available=Size(width=500, height=500))

        assert node.layout.width == 100
        assert node.layout.height == 50
        assert node.layout.x == 0
        assert node.layout.y == 0

    def test_row_layout(self):
        """Basic row layout with flex-grow."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=200, height=100))

        # Children split the 200px width
        assert child1.layout.width == 100
        assert child2.layout.width == 100
        assert child1.layout.x == 0
        assert child2.layout.x == 100

    def test_column_layout(self):
        """Column layout stacks vertically."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=100, height=200))

        assert child1.layout.height == 100
        assert child2.layout.height == 100
        assert child1.layout.y == 0
        assert child2.layout.y == 100

    def test_justify_center(self):
        """Justify content center."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                justify_content=JustifyContent.CENTER,
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(50)))

        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.x == 75

    def test_nested_layout(self):
        """Nested flex containers."""
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(200),
                flex_direction=FlexDirection.ROW,
            )
        )
        left = LayoutNode(style=FlexStyle(flex_grow=1.0))
        right = LayoutNode(style=FlexStyle(flex_grow=1.0, flex_direction=FlexDirection.COLUMN))
        right_top = LayoutNode(style=FlexStyle(flex_grow=1.0))
        right_bottom = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(left)
        root.add_child(right)
        right.add_child(right_top)
        right.add_child(right_bottom)

        compute_layout(root, available=Size(width=300, height=200))

        # Left and right split 300px
        assert left.layout.width == 150
        assert right.layout.width == 150
        assert right.layout.x == 150

        # Right's children split 200px height
        assert right_top.layout.height == 100
        assert right_bottom.layout.height == 100
        assert right_bottom.layout.y == 100

    def test_no_children(self):
        """Node without children gets its own size only."""
        node = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )

        compute_layout(node, available=Size(width=500, height=500))

        assert node.layout.width == 100
        assert node.layout.height == 50

    def test_dirty_flag_cleared(self):
        """compute_layout clears the dirty flag."""
        node = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        assert node.is_dirty()

        compute_layout(node, available=Size(width=500, height=500))

        assert not node.is_dirty()


class TestComputeLayoutBorder:
    """Tests for border support in compute_layout (Task 2.3)."""

    def test_border_reduces_inner_content_area_row(self):
        """Border should reduce available space for children in row layout."""
        from wtfui.tui.layout.types import Border

        # Container: 200x100, border: 10px all sides
        # Inner area should be: (200 - 20) x (100 - 20) = 180 x 80
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.all(10.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child should fill inner area (minus border)
        assert child.layout.width == 180  # 200 - (10 + 10)
        assert child.layout.height == 80  # 100 - (10 + 10)

    def test_border_offsets_children_position_row(self):
        """Children should be offset by border + padding in row layout."""
        from wtfui.tui.layout.types import Border, Spacing

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border(top=5.0, right=10.0, bottom=15.0, left=20.0),
                padding=Spacing.all(Dimension.points(10.0)),
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child should be offset by border.left + padding.left
        assert child.layout.x == 30  # border.left (20) + padding.left (10)
        # Child should be offset by border.top + padding.top
        assert child.layout.y == 15  # border.top (5) + padding.top (10)

    def test_border_reduces_inner_content_area_column(self):
        """Border should reduce available space for children in column layout."""
        from wtfui.tui.layout.types import Border

        # Container: 100x200, border: 10px all sides
        # Inner area should be: (100 - 20) x (200 - 20) = 80 x 180
        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
                border=Border.all(10.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=100, height=200))

        # Child should fill inner area (minus border)
        assert child.layout.width == 80  # 100 - (10 + 10)
        assert child.layout.height == 180  # 200 - (10 + 10)

    def test_border_offsets_children_position_column(self):
        """Children should be offset by border + padding in column layout."""
        from wtfui.tui.layout.types import Border, Spacing

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
                border=Border(top=8.0, right=6.0, bottom=4.0, left=12.0),
                padding=Spacing.all(Dimension.points(5.0)),
            )
        )
        child = LayoutNode(style=FlexStyle(width=Dimension.points(30), height=Dimension.points(50)))
        root.add_child(child)

        compute_layout(root, available=Size(width=100, height=200))

        # Child should be offset by border.left + padding.left
        assert child.layout.x == 17  # border.left (12) + padding.left (5)
        # Child should be offset by border.top + padding.top
        assert child.layout.y == 13  # border.top (8) + padding.top (5)

    def test_border_with_multiple_children_row(self):
        """Border should work correctly with multiple children in row layout."""
        from wtfui.tui.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(220),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.all(10.0),
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=220, height=100))

        # Inner width: 220 - 20 = 200, split between two children
        assert child1.layout.width == 100
        assert child2.layout.width == 100
        # First child starts at border.left
        assert child1.layout.x == 10
        # Second child follows first
        assert child2.layout.x == 110
        # Both offset by border.top
        assert child1.layout.y == 10
        assert child2.layout.y == 10

    def test_border_with_zero_values(self):
        """Zero border should behave the same as no border."""
        from wtfui.tui.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.zero(),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # No border, child fills entire container
        assert child.layout.width == 200
        assert child.layout.height == 100
        assert child.layout.x == 0
        assert child.layout.y == 0

    def test_border_with_asymmetric_values(self):
        """Border with different values per side should work correctly."""
        from wtfui.tui.layout.types import Border

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border(top=2.0, right=4.0, bottom=6.0, left=8.0),
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Inner width: 200 - (8 + 4) = 188
        assert child.layout.width == 188
        # Inner height: 100 - (2 + 6) = 92
        assert child.layout.height == 92
        # Offset by border.left and border.top
        assert child.layout.x == 8
        assert child.layout.y == 2


class TestDisplayNone:
    """Tests for display:none support in layout (Task 3.1)."""

    def test_display_none_has_zero_size(self):
        """Element with display:none should have zero size."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                width=Dimension.points(50),
                height=Dimension.points(50),
            )
        )
        root.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Child with display:none should have zero size
        assert child.layout.width == 0
        assert child.layout.height == 0
        assert child.layout.x == 0
        assert child.layout.y == 0

    def test_display_none_does_not_affect_siblings_row(self):
        """Hidden element should not affect layout of visible siblings in row."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                width=Dimension.points(100),
            )
        )
        child3 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)
        root.add_child(child3)

        compute_layout(root, available=Size(width=300, height=100))

        # Visible children should split the full 300px width (not affected by hidden child)
        assert child1.layout.width == 150
        assert child3.layout.width == 150
        assert child1.layout.x == 0
        assert child3.layout.x == 150

        # Hidden child should have zero size
        assert child2.layout.width == 0
        assert child2.layout.height == 0

    def test_display_none_does_not_affect_siblings_column(self):
        """Hidden element should not affect layout of visible siblings in column."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(300),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                height=Dimension.points(100),
            )
        )
        child3 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)
        root.add_child(child3)

        compute_layout(root, available=Size(width=100, height=300))

        # Visible children should split the full 300px height
        assert child1.layout.height == 150
        assert child3.layout.height == 150
        assert child1.layout.y == 0
        assert child3.layout.y == 150

        # Hidden child should have zero size
        assert child2.layout.width == 0
        assert child2.layout.height == 0

    def test_display_none_with_gap(self):
        """Hidden elements should not contribute to gap spacing."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                gap=10.0,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                width=Dimension.points(100),
            )
        )
        child3 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        root.add_child(child1)
        root.add_child(child2)
        root.add_child(child3)

        compute_layout(root, available=Size(width=300, height=100))

        # Only one gap should exist (between child1 and child3)
        assert child1.layout.x == 0
        assert child1.layout.width == 100
        assert child3.layout.x == 110  # 100 + 10 (gap), not 220
        assert child3.layout.width == 100

        # Hidden child
        assert child2.layout.width == 0
        assert child2.layout.height == 0

    def test_display_none_all_children(self):
        """Container with all hidden children should handle gracefully."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(display=Display.NONE))
        child2 = LayoutNode(style=FlexStyle(display=Display.NONE))

        root.add_child(child1)
        root.add_child(child2)

        compute_layout(root, available=Size(width=200, height=100))

        # All children should have zero size
        assert child1.layout.width == 0
        assert child1.layout.height == 0
        assert child2.layout.width == 0
        assert child2.layout.height == 0

    def test_display_none_nested(self):
        """Hidden parent should result in zero-sized descendants."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        parent = LayoutNode(
            style=FlexStyle(
                display=Display.NONE,
                flex_grow=1.0,
            )
        )
        child = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(parent)
        parent.add_child(child)

        compute_layout(root, available=Size(width=200, height=100))

        # Parent should have zero size
        assert parent.layout.width == 0
        assert parent.layout.height == 0

        # Child of hidden parent should also have zero size
        assert child.layout.width == 0
        assert child.layout.height == 0

    def test_display_none_with_fixed_and_flex(self):
        """Mix of display:none with fixed-size and flex-grow children."""
        from wtfui.tui.layout.style import Display

        root = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(400),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(display=Display.NONE, width=Dimension.points(50)))
        child3 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child4 = LayoutNode(style=FlexStyle(width=Dimension.points(150)))

        root.add_child(child1)
        root.add_child(child2)
        root.add_child(child3)
        root.add_child(child4)

        compute_layout(root, available=Size(width=400, height=100))

        # Fixed-size children
        assert child1.layout.width == 100
        assert child1.layout.x == 0

        # Hidden child
        assert child2.layout.width == 0
        assert child2.layout.height == 0

        # Flex child should take remaining space: 400 - 100 - 150 = 150
        assert child3.layout.width == 150
        assert child3.layout.x == 100

        # Fixed-size child
        assert child4.layout.width == 150
        assert child4.layout.x == 250


class TestRTLLayout:
    """Tests for RTL direction support (Task 4.2)."""

    def test_row_rtl_reverses_children(self):
        """Row direction in RTL lays out children right-to-left."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                direction=Direction.RTL,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(300, 100))

        # In RTL, first child appears on the right side
        assert child1.layout.x == 200  # 300 - 100
        assert child2.layout.x == 100  # 300 - 100 - 100

    def test_row_ltr_normal_order(self):
        """Row direction in LTR lays out children left-to-right (default)."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                direction=Direction.LTR,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(300, 100))

        # In LTR, first child appears on the left side
        assert child1.layout.x == 0
        assert child2.layout.x == 100

    def test_column_rtl_unchanged(self):
        """Column direction is not affected by RTL."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(300),
                flex_direction=FlexDirection.COLUMN,
                direction=Direction.RTL,
            )
        )
        child1 = LayoutNode(style=FlexStyle(height=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(height=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(100, 300))

        # Column layout is unaffected by RTL
        assert child1.layout.y == 0
        assert child2.layout.y == 100

    def test_row_reverse_rtl_becomes_normal(self):
        """Row-reverse in RTL becomes normal row order."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW_REVERSE,
                direction=Direction.RTL,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(300, 100))

        # In RTL, row-reverse becomes row (left-to-right)
        assert child1.layout.x == 0
        assert child2.layout.x == 100

    def test_rtl_with_gap(self):
        """RTL layout respects gap between children."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(320),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                direction=Direction.RTL,
                gap=10.0,
            )
        )
        child1 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child2 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        child3 = LayoutNode(style=FlexStyle(width=Dimension.points(100)))

        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)

        compute_layout(parent, Size(320, 100))

        # In RTL: child1 at right, child3 at left, with gaps
        # Total: 3 items * 100px + 2 gaps * 10px = 320px (perfect fit)
        assert child1.layout.x == 220  # 320 - 100 (rightmost)
        assert child2.layout.x == 110  # 320 - 100 - 10 - 100
        assert child3.layout.x == 0  # 320 - 100 - 10 - 100 - 10 - 100 (leftmost)

    def test_rtl_with_flex_grow(self):
        """RTL layout with flex-grow distributes space correctly."""
        from wtfui.tui.layout.style import Direction

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                direction=Direction.RTL,
            )
        )
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))
        child2 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        parent.add_child(child1)
        parent.add_child(child2)

        compute_layout(parent, Size(300, 100))

        # Both children should split the space, but positioned RTL
        assert child1.layout.width == 150
        assert child2.layout.width == 150
        assert child1.layout.x == 150  # First child on the right
        assert child2.layout.x == 0  # Second child on the left


class TestAutoMargins:
    """Tests for auto margins support (Task 5.2)."""

    def test_auto_margin_left_pushes_right_row(self):
        """Auto margin on left pushes item to the right in row layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.points(0),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child pushed to the right by auto left margin
        assert child.layout.x == 150  # 200 - 50
        assert child.layout.width == 50

    def test_auto_margin_right_stays_left_row(self):
        """Auto margin on right keeps item at left in row layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.points(0),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child stays at left with auto right margin
        assert child.layout.x == 0
        assert child.layout.width == 50

    def test_auto_margins_both_centers_row(self):
        """Auto margins on both left and right centers the item in row layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.x == 75
        assert child.layout.width == 50

    def test_auto_margin_top_pushes_bottom_column(self):
        """Auto margin on top pushes item to the bottom in column layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.points(0),
                    right=Dimension.points(0),
                    top=Dimension.auto(),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(100, 200))

        # Child pushed to the bottom by auto top margin
        assert child.layout.y == 150  # 200 - 50
        assert child.layout.height == 50

    def test_auto_margin_bottom_stays_top_column(self):
        """Auto margin on bottom keeps item at top in column layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.points(0),
                    right=Dimension.points(0),
                    top=Dimension.points(0),
                    bottom=Dimension.auto(),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(100, 200))

        # Child stays at top with auto bottom margin
        assert child.layout.y == 0
        assert child.layout.height == 50

    def test_auto_margins_both_centers_column(self):
        """Auto margins on both top and bottom centers the item in column layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(200),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.points(0),
                    right=Dimension.points(0),
                    top=Dimension.auto(),
                    bottom=Dimension.auto(),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(100, 200))

        # Child centered: (200 - 50) / 2 = 75
        assert child.layout.y == 75
        assert child.layout.height == 50

    def test_auto_margins_with_justify_content_center(self):
        """Auto margins work with justify-content center (single item overrides)."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                justify_content=JustifyContent.CENTER,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.points(0),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(200, 100))

        # Child has auto left margin, so it's pushed to the right (overrides justify-content)
        assert child.layout.x == 150  # 200 - 50

    def test_auto_margins_single_child_centered(self):
        """Single child with auto margins both sides is centered."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(300),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(300, 100))

        # Single child centered by auto margins: (300 - 50) / 2 = 125
        assert child.layout.x == 125
        assert child.layout.width == 50

    def test_auto_margins_single_child_centered_column(self):
        """Single child with auto margins both sides is centered in column."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(300),
                flex_direction=FlexDirection.COLUMN,
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                height=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.points(0),
                    right=Dimension.points(0),
                    top=Dimension.auto(),
                    bottom=Dimension.auto(),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(100, 300))

        # Single child centered by auto margins: (300 - 50) / 2 = 125
        assert child.layout.y == 125
        assert child.layout.height == 50

    def test_auto_margins_with_padding_row(self):
        """Auto margins work correctly with padding in row layout."""
        from wtfui.tui.layout.types import Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(220),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                padding=Spacing.all(Dimension.points(10)),
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(220, 100))

        # Inner width: 220 - 20 = 200
        # Child centered within inner space: (200 - 50) / 2 = 75
        # But offset by padding.left: 75 + 10 = 85
        assert child.layout.x == 85

    def test_auto_margins_with_border_row(self):
        """Auto margins work correctly with border in row layout."""
        from wtfui.tui.layout.types import Border, Spacing

        parent = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(220),
                height=Dimension.points(100),
                flex_direction=FlexDirection.ROW,
                border=Border.all(10),
            )
        )
        child = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                margin=Spacing(
                    left=Dimension.auto(),
                    right=Dimension.auto(),
                    top=Dimension.points(0),
                    bottom=Dimension.points(0),
                ),
            )
        )
        parent.add_child(child)

        compute_layout(parent, Size(220, 100))

        # Inner width: 220 - 20 = 200
        # Child centered within inner space: (200 - 50) / 2 = 75
        # But offset by border.left: 75 + 10 = 85
        assert child.layout.x == 85
