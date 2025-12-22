"""End-to-end integration tests for hover functionality.

Tests the complete hover flow:
- Mouse position -> hit testing -> style merge -> cell rendering
"""

from wtfui.core.protocol import RenderNode
from wtfui.core.style import Style
from wtfui.tui.renderer.renderer import ConsoleRenderer


class TestHoverE2E:
    """End-to-end tests for hover functionality."""

    def test_hover_changes_appearance_on_mouse_enter(self):
        """Complete flow: mouse enters element, style changes."""
        renderer = ConsoleRenderer(80, 24)

        # Create styled element
        style = Style(
            color="white",
            bg="slate-800",
            hover=Style(bg="blue-600", font_weight="bold"),
        )

        node = RenderNode(
            tag="Button",
            element_id=1,
            label="Click Me",
            props={
                "style": {
                    "left": 10,
                    "top": 5,
                    "width": 10,
                    "height": 1,
                    "_wtfui_style": style,
                }
            },
        )

        # Initial render - mouse outside
        renderer.update_mouse(0, 0)
        renderer.render_node_with_layout(node)

        cell_outside = renderer.back_buffer.get(10, 5)
        assert cell_outside.bg == (30, 41, 59)  # slate-800
        assert cell_outside.bold is False

        # Mouse enters
        renderer.clear()
        renderer.update_mouse(12, 5)  # Inside button
        renderer.render_node_with_layout(node)

        cell_hover = renderer.back_buffer.get(10, 5)
        assert cell_hover.bg == (37, 99, 235)  # blue-600
        assert cell_hover.bold is True

    def test_hover_reverts_on_mouse_leave(self):
        """Style reverts when mouse leaves element."""
        renderer = ConsoleRenderer(80, 24)

        style = Style(
            color="white",
            bg="slate-800",
            hover=Style(bg="blue-600"),
        )

        node = RenderNode(
            tag="Button",
            element_id=1,
            label="Click Me",
            props={
                "style": {
                    "left": 10,
                    "top": 5,
                    "width": 10,
                    "height": 1,
                    "_wtfui_style": style,
                }
            },
        )

        # Hover
        renderer.update_mouse(12, 5)
        renderer.render_node_with_layout(node)
        assert renderer.back_buffer.get(10, 5).bg == (37, 99, 235)  # blue-600

        # Leave
        renderer.clear()
        renderer.update_mouse(50, 20)  # Far away
        renderer.render_node_with_layout(node)
        assert renderer.back_buffer.get(10, 5).bg == (30, 41, 59)  # slate-800

    def test_nested_elements_hover_independently(self):
        """Nested elements should have independent hover states."""
        renderer = ConsoleRenderer(80, 24)

        outer_style = Style(bg="slate-700", hover=Style(bg="slate-600"))
        inner_style = Style(bg="blue-800", hover=Style(bg="blue-600"))

        outer = RenderNode(
            tag="Div",
            element_id=1,
            props={
                "style": {
                    "left": 0,
                    "top": 0,
                    "width": 20,
                    "height": 3,
                    "_wtfui_style": outer_style,
                }
            },
            children=[
                RenderNode(
                    tag="Text",
                    element_id=2,
                    text_content="Inner",
                    props={
                        "style": {
                            "left": 5,
                            "top": 1,
                            "width": 5,
                            "height": 1,
                            "_wtfui_style": inner_style,
                        }
                    },
                )
            ],
        )

        # Mouse over inner element
        renderer.update_mouse(6, 1)
        renderer.render_node_with_layout(outer)

        # Inner should be hovered
        inner_cell = renderer.back_buffer.get(6, 1)
        assert inner_cell.bg == (37, 99, 235)  # blue-600 (hover)
