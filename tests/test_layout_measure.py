# tests/test_layout_measure.py
import pytest

from flow.layout.algorithm import AvailableSpace
from flow.layout.measure import MeasureContext, create_text_measure
from flow.layout.types import Size


class TestMeasureFunc:
    def test_measure_func_protocol(self):
        """MeasureFunc returns Size given available space."""

        def simple_measure(
            available_width: AvailableSpace,
            available_height: AvailableSpace,
            context: MeasureContext,
        ) -> Size:
            # Fixed size regardless of available space
            return Size(width=100, height=20)

        result = simple_measure(
            AvailableSpace.definite(500),
            AvailableSpace.definite(500),
            MeasureContext(),
        )
        assert result.width == 100
        assert result.height == 20

    def test_text_measure_character_count(self):
        """Character-based text measurement for server-side."""
        measure = create_text_measure(
            text="Hello World",
            font_size=16,
            chars_per_em=0.5,  # Rough estimate
        )

        result = measure(
            AvailableSpace.max_content(),
            AvailableSpace.max_content(),
            MeasureContext(),
        )

        # 11 chars * 16px * 0.5 = 88px width
        assert result.width == 88
        # Single line height
        assert result.height == 16 * 1.2  # line-height factor

    def test_text_measure_wrapping(self):
        """Text wraps when constrained width."""
        measure = create_text_measure(
            text="Hello World",
            font_size=16,
            chars_per_em=0.5,
        )

        result = measure(
            AvailableSpace.definite(50),  # Constrain width
            AvailableSpace.max_content(),
            MeasureContext(),
        )

        # Text should wrap to multiple lines
        assert result.width <= 50
        assert result.height > 16 * 1.2  # More than one line


class TestMeasureContext:
    def test_context_has_renderer_hint(self):
        """Context can carry renderer-specific hints."""
        ctx = MeasureContext(renderer="html", font_family="sans-serif")
        assert ctx.renderer == "html"
        assert ctx.font_family == "sans-serif"


class TestLayoutNodeWithMeasure:
    def test_node_accepts_measure_func(self):
        """LayoutNode can have a measure function."""
        from flow.layout.node import LayoutNode
        from flow.layout.style import FlexStyle

        def my_measure(w, h, ctx):
            return Size(width=50, height=25)

        node = LayoutNode(
            style=FlexStyle(),
            measure_func=my_measure,
        )

        assert node.measure_func is not None
        assert node.measure_func(
            AvailableSpace.max_content(),
            AvailableSpace.max_content(),
            MeasureContext(),
        ) == Size(width=50, height=25)

    def test_leaf_node_with_measure_has_no_children(self):
        """Nodes with measure_func are leaf nodes."""
        from flow.layout.node import LayoutNode
        from flow.layout.style import FlexStyle

        node = LayoutNode(
            style=FlexStyle(),
            measure_func=lambda w, h, c: Size(50, 25),
        )

        # Cannot add children to a measured node
        child = LayoutNode(style=FlexStyle())
        with pytest.raises(ValueError, match="measured node"):
            node.add_child(child)
