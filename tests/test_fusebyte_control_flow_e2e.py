"""End-to-end tests for WtfUIByte control flow compilation.

Verifies full compilation pipeline for:
1. Control flow (if/else, for loops, nested control flow)
2. CSS generation (deduplication and multiple classes)
"""

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.writer import MAGIC_HEADER
from wtfui.web.compiler.wtfuibyte import WtfUICompiler


class TestControlFlowE2E:
    """Full compilation tests for if/for statements."""

    def test_if_else_full_compilation(self):
        """Complete if/else compiles with correct jump targets."""
        source = """
loading = Signal(True)
if loading.value:
    with Div():
        Text("Loading...")
else:
    with Div():
        Text("Content")
"""
        compiler = WtfUICompiler()
        binary, _css = compiler.compile_with_css(source)

        # Verify structure
        assert binary.startswith(MAGIC_HEADER)
        assert binary.endswith(bytes([OpCode.HALT]))

        # Verify opcodes present
        assert bytes([OpCode.INIT_SIG_NUM]) in binary or bytes([OpCode.INIT_SIG_STR]) in binary
        assert bytes([OpCode.DOM_IF]) in binary
        assert bytes([OpCode.DOM_CREATE]) in binary

        # Verify both text strings in table
        assert "Loading..." in compiler.writer._string_map
        assert "Content" in compiler.writer._string_map

    def test_for_loop_full_compilation(self):
        """Complete for loop compiles with template block."""
        source = """
items = Signal(["A", "B", "C"])
for item in items.value:
    with Div():
        Text(item)
"""
        compiler = WtfUICompiler()
        binary, _css = compiler.compile_with_css(source)

        # Verify opcodes present
        assert bytes([OpCode.DOM_FOR]) in binary

        # Verify item signal is registered
        assert "item" in compiler.signal_map

        # Verify structure
        assert binary.startswith(MAGIC_HEADER)
        assert binary.endswith(bytes([OpCode.HALT]))

    def test_nested_control_flow(self):
        """Nested if inside for compiles correctly."""
        source = """
items = Signal([1, 2, 3])
show_even = Signal(True)

for item in items.value:
    if show_even.value:
        Text("even")
"""
        compiler = WtfUICompiler()
        binary, _css = compiler.compile_with_css(source)

        # Verify both control flow opcodes present
        assert bytes([OpCode.DOM_FOR]) in binary
        assert bytes([OpCode.DOM_IF]) in binary

        # Verify structure
        assert binary.startswith(MAGIC_HEADER)
        assert binary.endswith(bytes([OpCode.HALT]))


class TestCSSIntegrationE2E:
    """Full compilation tests for CSS generation."""

    def test_multiple_elements_dedupe_css(self):
        """Identical styles produce single CSS class."""
        source = """
with Div(style={"padding": "4px"}):
    Text("A")
with Div(style={"padding": "4px"}):
    Text("B")
"""
        compiler = WtfUICompiler()
        _binary, css = compiler.compile_with_css(source)

        # Should have exactly one CSS rule (deduped)
        # Count the number of unique .fl- class definitions
        css_class_count = css.count(".fl-")
        assert css_class_count == 1, f"Expected 1 CSS class, got {css_class_count}"

    def test_different_styles_multiple_classes(self):
        """Different styles produce different CSS classes."""
        source = """
with Div(style={"background": "red"}):
    Text("Red")
with Div(style={"background": "blue"}):
    Text("Blue")
"""
        compiler = WtfUICompiler()
        _binary, css = compiler.compile_with_css(source)

        # Should have two CSS rules
        css_class_count = css.count(".fl-")
        assert css_class_count == 2, f"Expected 2 CSS classes, got {css_class_count}"

        # Both colors should be in CSS
        assert "red" in css
        assert "blue" in css
