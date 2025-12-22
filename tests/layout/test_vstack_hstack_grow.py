# tests/layout/test_vstack_hstack_grow.py
"""Tests for VStack/HStack flex_grow behavior with explicit dimensions.

These tests verify that VStack/HStack respect explicit height/width
and don't apply flex_grow=1 when dimensions are explicitly set.
"""

from wtfui.core.context import reset_parent, set_current_parent
from wtfui.core.style import Style
from wtfui.tui.adapter import LayoutAdapter
from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.types import Size
from wtfui.ui import HStack, Text, VStack


class _CaptureParent:
    """Mock parent to capture element tree for testing."""

    def __init__(self):
        self.children: list = []

    def invalidate_layout(self):
        pass


class TestVStackHStackGrow:
    """Test VStack/HStack flex_grow behavior."""

    def test_hstack_explicit_height_no_grow(self):
        """HStack with explicit h should not grow beyond that height in column parent."""
        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            with VStack(style=Style(h="100%")) as root:
                with HStack(style=Style(h=3)):
                    Text("Header")
                with HStack(style=Style(flex_grow=1)):
                    Text("Main")
                with HStack(style=Style(h=3)):
                    Text("Footer")
        finally:
            reset_parent(token)

        # Compute layout
        layout = LayoutAdapter().to_layout_node(root)
        compute_layout(layout, Size(80, 24))

        # Header should be exactly 3, not expanded
        assert layout.children[0].layout.height == 3, (
            f"Header should be h=3, got {layout.children[0].layout.height}"
        )
        # Footer should be exactly 3, not expanded
        assert layout.children[2].layout.height == 3, (
            f"Footer should be h=3, got {layout.children[2].layout.height}"
        )
        # Main should fill remaining space (24 - 3 - 3 = 18)
        assert layout.children[1].layout.height == 18, (
            f"Main should be h=18, got {layout.children[1].layout.height}"
        )

    def test_vstack_explicit_width_no_grow(self):
        """VStack with explicit w should not grow beyond that width in row parent."""
        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            with HStack(style=Style(w="100%")) as root:
                with VStack(style=Style(w=20)):
                    Text("Sidebar")
                with VStack(style=Style(flex_grow=1)):
                    Text("Main")
                with VStack(style=Style(w=20)):
                    Text("Sidebar")
        finally:
            reset_parent(token)

        # Compute layout
        layout = LayoutAdapter().to_layout_node(root)
        compute_layout(layout, Size(80, 24))

        # Left sidebar should be exactly 20, not expanded
        assert layout.children[0].layout.width == 20, (
            f"Left sidebar should be w=20, got {layout.children[0].layout.width}"
        )
        # Right sidebar should be exactly 20, not expanded
        assert layout.children[2].layout.width == 20, (
            f"Right sidebar should be w=20, got {layout.children[2].layout.width}"
        )
        # Main should fill remaining space (80 - 20 - 20 = 40)
        assert layout.children[1].layout.width == 40, (
            f"Main should be w=40, got {layout.children[1].layout.width}"
        )

    def test_hstack_no_height_no_auto_grow(self):
        """HStack without explicit height should NOT auto-grow.

        This is the intentional behavior change from CSS Flexbox.
        Use explicit flex_grow=1 when you want elements to expand.
        """
        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            with VStack(style=Style(h="100%")) as root:
                with HStack():
                    Text("Row 1")
                with HStack():
                    Text("Row 2")
        finally:
            reset_parent(token)

        # Compute layout
        layout = LayoutAdapter().to_layout_node(root)
        compute_layout(layout, Size(80, 24))

        # Both rows should have content height (1 for Text), NOT auto-expand
        assert layout.children[0].layout.height == 1, (
            f"Row 1 should have content height 1, got {layout.children[0].layout.height}"
        )
        assert layout.children[1].layout.height == 1, (
            f"Row 2 should have content height 1, got {layout.children[1].layout.height}"
        )

    def test_explicit_flex_grow_zero_respected(self):
        """Explicit flex_grow=0 should prevent growth."""
        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            with VStack(style=Style(h="100%")) as root:
                with HStack(style=Style(flex_grow=0)):
                    Text("Fixed row")
                with HStack(style=Style(flex_grow=1)):
                    Text("Growing row")
        finally:
            reset_parent(token)

        # Compute layout
        layout = LayoutAdapter().to_layout_node(root)
        compute_layout(layout, Size(80, 24))

        # First row should have minimal height (just for text)
        assert layout.children[0].layout.height == 1, (
            f"Fixed row should be h=1, got {layout.children[0].layout.height}"
        )
        # Second row should fill remaining space
        assert layout.children[1].layout.height == 23, (
            f"Growing row should be h=23, got {layout.children[1].layout.height}"
        )

    def test_percentage_height_no_grow(self):
        """HStack with percentage height should not grow beyond that."""
        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            with VStack(style=Style(h="100%")) as root:
                with HStack(style=Style(h="25%")):
                    Text("Quarter")
                with HStack(style=Style(flex_grow=1)):
                    Text("Rest")
        finally:
            reset_parent(token)

        # Compute layout
        layout = LayoutAdapter().to_layout_node(root)
        compute_layout(layout, Size(80, 24))

        # Quarter row should be 25% of 24 = 6
        assert layout.children[0].layout.height == 6, (
            f"Quarter row should be h=6, got {layout.children[0].layout.height}"
        )
        # Rest should fill remaining space (24 - 6 = 18)
        assert layout.children[1].layout.height == 18, (
            f"Rest row should be h=18, got {layout.children[1].layout.height}"
        )
