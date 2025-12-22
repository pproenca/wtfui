# tests/web/test_web_sovereignty.py
"""Litmus tests for Web sovereignty.

Web (wtfui.web) owns browser-specific concerns:
- Compiler (wtfui.web.compiler) - WtfUIByte bytecode generation
- DOM rendering (future)
- WASM integration (future)
"""


class TestWebSovereignty:
    """Verify Web sovereignty over browser-specific concerns."""

    def test_compiler_lives_in_web_package(self):
        """Compiler should be in wtfui.web.compiler."""
        from wtfui.web.compiler.wtfuibyte import compile_to_wtfuibyte

        # Compile a simple expression
        source = "x = 1 + 2"
        bytecode = compile_to_wtfuibyte(source)

        assert bytecode is not None
        assert len(bytecode) > 0

    def test_web_compiler_wtfuibyte_works(self):
        """wtfui.web.compiler.wtfuibyte can compile expressions."""
        from wtfui.web.compiler.wtfuibyte import compile_to_wtfuibyte

        source = "y = 3 * 4"
        bytecode = compile_to_wtfuibyte(source)

        assert bytecode is not None
        assert len(bytecode) > 0

    def test_split_brain_analyzer_in_web_compiler(self):
        """SplitBrainAnalyzer for client/server classification should be in web.compiler."""
        from wtfui.web.compiler.analyzer import ModuleType, SplitBrainAnalyzer
        from wtfui.web.compiler.graph import DependencyGraph

        # Create a minimal graph for the analyzer
        graph = DependencyGraph()
        analyzer = SplitBrainAnalyzer(graph)

        # Verifying it can be instantiated and module types are accessible
        assert analyzer is not None
        assert ModuleType.CLIENT is not None
        assert ModuleType.SERVER is not None

    def test_boundary_sentinel_in_web_compiler(self):
        """BoundarySentinel for bundle optimization should be in web.compiler."""
        from wtfui.web.compiler.validator import BoundarySentinel

        # Just verifying it can be imported from the new location
        assert BoundarySentinel is not None

    def test_parallel_compiler_in_web_package(self):
        """ParallelCompiler for No-GIL compilation should be in web.compiler."""
        from wtfui.web.compiler.parallel import ParallelCompiler, ShardedStringPool

        # Just verifying imports work from the new location
        assert ParallelCompiler is not None
        assert ShardedStringPool is not None

    def test_compiler_does_not_require_tui(self):
        """Web compiler should work without forcing TUI dependencies."""
        import sys

        # Record TUI modules before
        tui_prefixes = ("wtfui.tui.layout", "wtfui.tui.adapter")
        before = {m for m in sys.modules if m.startswith(tui_prefixes)}

        # Import compiler
        from wtfui.web.compiler.wtfuibyte import compile_to_wtfuibyte

        # Compile without needing TUI
        source = "z = 5 + 5"
        bytecode = compile_to_wtfuibyte(source)

        assert bytecode is not None

        # Check that compiler didn't load new TUI modules
        after = {m for m in sys.modules if m.startswith(tui_prefixes)}
        newly_loaded = after - before

        assert not newly_loaded, f"TUI modules loaded by web compiler: {newly_loaded}"
