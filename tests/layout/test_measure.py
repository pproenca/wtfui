# tests/test_layout_measure.py
import pytest

from wtfui.tui.layout.algorithm import AvailableSpace
from wtfui.tui.layout.measure import MeasureContext, create_text_measure
from wtfui.tui.layout.types import Size


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


class TestCanvasTextMeasure:
    """Tests for Wasm canvas text measurement bridge."""

    def test_canvas_measure_fallback_without_js(self):
        """Without js module, falls back to character estimation."""
        from wtfui.tui.layout.measure import create_canvas_text_measure
        from wtfui.tui.layout.types import Size

        measure = create_canvas_text_measure("Hello", "16px sans-serif")

        # Create mock available space
        from wtfui.tui.layout.algorithm import AvailableSpace
        from wtfui.tui.layout.measure import MeasureContext

        width = AvailableSpace.definite(100)
        height = AvailableSpace.definite(100)
        ctx = MeasureContext(renderer="dom")

        result = measure(width, height, ctx)

        # Should return Size with reasonable dimensions (fallback behavior)
        assert isinstance(result, Size)
        assert result.width > 0
        assert result.height > 0

    def test_canvas_measure_uses_js_when_available(self, monkeypatch):
        """Uses canvas.measureText when js module available."""
        import sys
        from unittest.mock import MagicMock

        from wtfui.tui.layout.measure import MeasureContext, create_canvas_text_measure
        from wtfui.tui.layout.types import Size

        # Mock js module with canvas support
        mock_js = MagicMock()
        mock_canvas = MagicMock()
        mock_ctx = MagicMock()

        # measureText returns TextMetrics with width
        mock_metrics = MagicMock()
        mock_metrics.width = 42.5
        mock_ctx.measureText.return_value = mock_metrics

        mock_canvas.getContext.return_value = mock_ctx
        mock_js.document.createElement.return_value = mock_canvas

        # Inject mock js module
        monkeypatch.setitem(sys.modules, "js", mock_js)

        try:
            measure = create_canvas_text_measure("Hello", "16px sans-serif")

            from wtfui.tui.layout.algorithm import AvailableSpace

            width = AvailableSpace.definite(100)
            height = AvailableSpace.definite(100)
            ctx = MeasureContext(renderer="dom")

            result = measure(width, height, ctx)

            assert isinstance(result, Size)
            # Width should come from measureText (42.5)
            assert result.width == 42.5
        finally:
            # Clean up - remove mock
            if "js" in sys.modules and sys.modules["js"] is mock_js:
                del sys.modules["js"]


class TestLayoutNodeWithMeasure:
    def test_node_accepts_measure_func(self):
        """LayoutNode can have a measure function."""
        from wtfui.tui.layout.node import LayoutNode
        from wtfui.tui.layout.style import FlexStyle

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
        from wtfui.tui.layout.node import LayoutNode
        from wtfui.tui.layout.style import FlexStyle

        node = LayoutNode(
            style=FlexStyle(),
            measure_func=lambda w, h, c: Size(50, 25),
        )

        # Cannot add children to a measured node
        child = LayoutNode(style=FlexStyle())
        with pytest.raises(ValueError, match="measured node"):
            node.add_child(child)
