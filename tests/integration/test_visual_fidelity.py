"""Integration tests for Phase 3: Visual Fidelity.

These tests verify that both fixes work together correctly:
1. Parallel CSS generation produces output
2. Text measurement works in simulated browser environment
"""


class TestVisualFidelityIntegration:
    """End-to-end tests for visual fidelity features."""

    def test_parallel_build_produces_css(self):
        """Parallel compilation produces CSS file content."""
        from wtfui.web.compiler.parallel import ParallelCompiler

        source = """
with Div(style={"background": "blue", "padding": "10px"}):
    with Text(style={"color": "white"}):
        pass
"""
        compiler = ParallelCompiler()
        binary = compiler.compile(source)
        css = compiler.get_merged_css()

        # Should have bytecode
        assert len(binary) > 0

        # Should have CSS with both styles
        assert "background: blue" in css or "background" in css
        assert "padding" in css or "color" in css

    def test_single_file_build_produces_css(self):
        """Single-unit builds (most common case) produce CSS."""
        from wtfui.web.compiler.parallel import ParallelCompiler

        # Simple single-widget app
        source = """
with Button(style={"width": "200px", "height": "50px"}):
    pass
"""
        compiler = ParallelCompiler()
        compiler.compile(source)
        css = compiler.get_merged_css()

        # Must have width and height
        assert "width" in css, f"CSS missing width: {css}"
        assert "height" in css, f"CSS missing height: {css}"

    def test_text_measure_consistency(self):
        """Text measurement is consistent between calls."""
        from wtfui.tui.layout.algorithm import AvailableSpace
        from wtfui.tui.layout.measure import MeasureContext, create_canvas_text_measure

        text = "Hello World"
        font = "16px sans-serif"

        measure1 = create_canvas_text_measure(text, font)
        measure2 = create_canvas_text_measure(text, font)

        ctx = MeasureContext(renderer="dom")
        width = AvailableSpace.definite(200)
        height = AvailableSpace.definite(100)

        result1 = measure1(width, height, ctx)
        result2 = measure2(width, height, ctx)

        # Same input should give same output
        assert result1.width == result2.width
        assert result1.height == result2.height
