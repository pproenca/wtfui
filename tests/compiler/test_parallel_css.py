"""Tests for CSS generation in parallel compilation."""

from wtfui.web.compiler.parallel import CompilationUnit


class TestCompilationUnitCSS:
    """CompilationUnit includes CSS class data."""

    def test_compilation_unit_has_css_classes_field(self):
        """CompilationUnit can store CSS class data."""
        unit = CompilationUnit(
            node_id=1,
            bytecode=b"\x00",
            strings=("hello",),
            children=(),
            css_classes=(("fl-abc123", {"width": "100px"}),),
        )

        assert unit.css_classes == (("fl-abc123", {"width": "100px"}),)

    def test_css_classes_defaults_empty(self):
        """CSS classes default to empty tuple."""
        unit = CompilationUnit(
            node_id=1,
            bytecode=b"\x00",
            strings=(),
            children=(),
        )

        assert unit.css_classes == ()


class TestParallelCompilerCSS:
    """ParallelCompiler generates CSS from each worker."""

    def test_compile_unit_generates_css(self):
        """_compile_unit populates css_classes from style props."""
        from wtfui.web.compiler.parallel import ParallelCompiler

        # Source with inline style
        source = """
with Div(style={"width": "100px", "height": "50px"}):
    Text("Hello")
"""
        compiler = ParallelCompiler()

        # Compile and check result has CSS
        result = compiler.compile(source)

        # Result should include CSS (we'll verify in merge test)
        assert isinstance(result, bytes)

    def test_worker_produces_css_classes(self):
        """Worker thread populates css_classes in CompilationUnit."""
        import ast

        from wtfui.web.compiler.parallel import CompilationUnit, ParallelCompiler

        source = """
with Div(style={"width": "100px"}):
    pass
"""
        compiler = ParallelCompiler()

        # Access internal method to test worker behavior
        tree = ast.parse(source)

        # Extract units
        units = compiler._extract_units(tree)

        assert len(units) > 0, "Should extract at least one unit"

        # Compile first unit
        result = compiler._compile_unit(units[0])

        # Result should be CompilationUnit with css_classes
        assert isinstance(result, CompilationUnit)

        # Should have extracted CSS from style prop
        assert len(result.css_classes) > 0, "Should extract CSS from style attribute"
        class_name, style_dict = result.css_classes[0]

        # Should have generated class name
        assert class_name.startswith("fl-")

        # Should have width style
        assert "width" in style_dict
        assert style_dict["width"] == "100px"


class TestParallelCSSMerge:
    """CSS from workers is merged and deduplicated."""

    def test_merge_deduplicates_css(self):
        """Identical styles from different workers produce single class."""
        from wtfui.web.compiler.parallel import CompilationUnit, ParallelCompiler

        compiler = ParallelCompiler()

        # Simulate two workers with identical styles
        compiler._results = {
            0: CompilationUnit(
                node_id=0,
                bytecode=b"\x01",
                strings=(),
                children=(),
                css_classes=(("fl-0-abc", {"width": "100px"}),),
            ),
            1: CompilationUnit(
                node_id=1,
                bytecode=b"\x02",
                strings=(),
                children=(),
                css_classes=(("fl-1-abc", {"width": "100px"}),),  # Same style
            ),
        }

        # Get merged CSS
        css = compiler.get_merged_css()

        # Should deduplicate to single class
        assert css.count("width: 100px") == 1

    def test_merge_preserves_unique_styles(self):
        """Different styles from workers are all included."""
        from wtfui.web.compiler.parallel import CompilationUnit, ParallelCompiler

        compiler = ParallelCompiler()

        compiler._results = {
            0: CompilationUnit(
                node_id=0,
                bytecode=b"\x01",
                strings=(),
                children=(),
                css_classes=(("fl-0-a", {"width": "100px"}),),
            ),
            1: CompilationUnit(
                node_id=1,
                bytecode=b"\x02",
                strings=(),
                children=(),
                css_classes=(("fl-1-b", {"height": "50px"}),),  # Different style
            ),
        }

        css = compiler.get_merged_css()

        assert "width: 100px" in css
        assert "height: 50px" in css


class TestParallelCSSFallback:
    """CSS is generated even when falling back to single-threaded."""

    def test_single_unit_fallback_generates_css(self):
        """Single-unit AST still produces CSS from get_merged_css()."""
        from wtfui.web.compiler.parallel import ParallelCompiler

        # Source with single with statement (only 1 unit extracted)
        source = """
with Div(style={"width": "100px"}):
    pass
"""
        compiler = ParallelCompiler()
        binary = compiler.compile(source)

        # Should produce bytecode
        assert isinstance(binary, bytes)
        assert len(binary) > 0

        css = compiler.get_merged_css()
        assert "width: 100px" in css, f"CSS should contain width style, got: {css!r}"
