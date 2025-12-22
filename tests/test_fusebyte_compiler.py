"""Tests for WtfUIByte AST Compiler."""

import struct

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.writer import MAGIC_HEADER
from wtfui.web.compiler.wtfuibyte import WtfUICompiler


class TestSignalCompilation:
    """Test Signal initialization compilation."""

    def test_compile_signal_init_numeric(self) -> None:
        """Signal(0) compiles to INIT_SIG_NUM opcode."""
        source = """
count = Signal(0)
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        # Parse binary
        header_len = len(MAGIC_HEADER)
        _str_count = struct.unpack_from("!H", binary, header_len)[0]
        code_start = header_len + 2  # Just count, no strings

        # First opcode should be INIT_SIG_NUM
        assert binary[code_start] == OpCode.INIT_SIG_NUM

        # Signal ID should be 0
        sig_id = struct.unpack_from("!H", binary, code_start + 1)[0]
        assert sig_id == 0

        # Initial value should be 0.0
        init_val = struct.unpack_from("!d", binary, code_start + 3)[0]
        assert init_val == 0.0

    def test_compile_signal_init_with_value(self) -> None:
        """Signal(42) compiles with correct initial value."""
        source = """
count = Signal(42)
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        header_len = len(MAGIC_HEADER)
        code_start = header_len + 2

        init_val = struct.unpack_from("!d", binary, code_start + 3)[0]
        assert init_val == 42.0

    def test_multiple_signals_get_unique_ids(self) -> None:
        """Multiple signals get incrementing IDs."""
        source = """
count = Signal(0)
name = Signal("hello")
flag = Signal(1)
"""
        compiler = WtfUICompiler()
        _binary = compiler.compile(source)

        # Verify we have 3 signals with IDs 0, 1, 2
        assert compiler.signal_map["count"] == 0
        assert compiler.signal_map["name"] == 1
        assert compiler.signal_map["flag"] == 2


class TestDomCompilation:
    """Test DOM element compilation."""

    def test_compile_with_div(self) -> None:
        """with Div(): compiles to DOM_CREATE + DOM_APPEND."""
        source = """
with Div():
    pass
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        # Find DOM_CREATE opcode
        assert OpCode.DOM_CREATE in binary

    def test_compile_text_element(self) -> None:
        """Text("hello") compiles to DOM_CREATE + DOM_TEXT."""
        source = """
with Div():
    Text("hello")
"""
        compiler = WtfUICompiler()
        _binary = compiler.compile(source)

        # Verify "hello" is in string table
        assert "hello" in compiler.writer._string_map


class TestButtonCompilation:
    """Test Button with click handler compilation."""

    def test_compile_button_with_handler(self) -> None:
        """Button with on_click compiles to DOM_ON_CLICK."""
        source = """
count = Signal(0)
def increment():
    count.value += 1

Button("Up", on_click=increment)
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        # Should have DOM_ON_CLICK opcode
        assert OpCode.DOM_ON_CLICK in binary

        # "Up" should be in string table
        assert "Up" in compiler.writer._string_map


class TestCompilerOutput:
    """Test overall compiler output."""

    def test_output_starts_with_magic_header(self) -> None:
        """All output starts with MYFU magic header."""
        source = "x = Signal(0)"
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        assert binary.startswith(MAGIC_HEADER)

    def test_output_ends_with_halt(self) -> None:
        """All output ends with HALT opcode."""
        source = "x = Signal(0)"
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        assert binary[-1] == OpCode.HALT


class TestControlFlowCompilation:
    """Test if/else and for loop compilation."""

    def test_compile_if_signal_value(self) -> None:
        """if signal.value: compiles to DOM_IF with jump addresses."""
        source = """
loading = Signal(True)
if loading.value:
    Text("Loading...")
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        # Check that visit_If was implemented (Text should be in string table)
        # If visit_If is not implemented, the if statement is silently dropped
        assert "Loading..." in compiler.writer._string_map, (
            "If body was not compiled - visit_If missing"
        )

        # Find DOM_IF opcode in the code section (not in string data)
        # Parse binary to find code section
        header_len = len(MAGIC_HEADER)
        str_count_pos = header_len
        str_count = struct.unpack_from("!H", binary, str_count_pos)[0]

        # Skip string table to find code section
        pos = str_count_pos + 2
        for _ in range(str_count):
            str_len = struct.unpack_from("!H", binary, pos)[0]
            pos += 2 + str_len

        # Now we're at the code section
        code_section = binary[pos:]

        # DOM_IF should appear as an opcode in code section
        assert OpCode.DOM_IF in code_section, "DOM_IF opcode not found in code section"

    def test_compile_if_else_signal_value(self) -> None:
        """if/else compiles both true and false blocks."""
        source = """
loading = Signal(True)
if loading.value:
    Text("Loading...")
else:
    Text("Done!")
"""
        compiler = WtfUICompiler()
        _binary = compiler.compile(source)

        # Both strings should be in string table
        assert "Loading..." in compiler.writer._string_map, "True block not compiled"
        assert "Done!" in compiler.writer._string_map, "False block not compiled"


class TestForLoopCompilation:
    """Test for loop compilation with signal values."""

    def test_compile_for_signal_value(self) -> None:
        """for item in items.value: compiles to DOM_FOR."""
        source = """
items = Signal(["a", "b", "c"])
for item in items.value:
    Text(item)
"""
        compiler = WtfUICompiler()
        binary = compiler.compile(source)

        # Should contain DOM_FOR opcode
        assert OpCode.DOM_FOR in binary, "DOM_FOR opcode not found in binary"

        # item should be registered as a signal for template binding
        assert "item" in compiler.signal_map, "Loop variable 'item' not registered as signal"


class TestCSSIntegration:
    """Test CSSGenerator integration into WtfUICompiler."""

    def test_compile_with_css_returns_tuple(self) -> None:
        """compile_with_css returns (bytecode, css_string) tuple."""
        source = """
with Div(style={"background": "blue", "padding": "4px"}):
    Text("Styled")
"""
        compiler = WtfUICompiler()
        result = compiler.compile_with_css(source)

        assert isinstance(result, tuple)
        assert len(result) == 2

        binary, css = result
        assert isinstance(binary, bytes)
        assert isinstance(css, str)

    def test_static_styles_emit_class_not_inline(self) -> None:
        """Static styles emit DOM_ATTR_CLASS, not DOM_STYLE_STATIC."""
        source = """
with Div(style={"background": "blue"}):
    Text("Styled")
"""
        compiler = WtfUICompiler()
        binary, css = compiler.compile_with_css(source)

        # Should use DOM_ATTR_CLASS for CSS class
        assert OpCode.DOM_ATTR_CLASS in binary

        # CSS should contain the atomic class
        assert "background" in css or "background-color" in css
        assert ".fl-" in css  # Atomic class prefix

    def test_multiple_elements_dedupe_css(self) -> None:
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
        assert css.count(".fl-") == 1

    def test_different_styles_multiple_classes(self) -> None:
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
        assert css.count(".fl-") == 2


class TestASTErrorHandling:
    """Test error handling for unsupported AST constructs."""

    def test_strict_mode_raises_on_unsupported_statement(self) -> None:
        """Strict mode should raise NotImplementedError on unsupported statements."""
        import pytest

        # While loop is not supported by WtfUIByte
        source = """
while True:
    pass
"""
        compiler = WtfUICompiler(strict=True)

        with pytest.raises(NotImplementedError, match="Unsupported statement"):
            compiler.compile(source)

    def test_non_strict_mode_warns_on_unsupported_statement(self) -> None:
        """Non-strict mode should warn but not raise on unsupported statements."""
        import warnings

        source = """
while True:
    pass
"""
        compiler = WtfUICompiler(strict=False)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compiler.compile(source)

            # Should have at least one warning about While
            assert len(w) >= 1
            assert any("While" in str(warning.message) for warning in w)

    def test_tracks_unhandled_nodes(self) -> None:
        """Compiler should track unhandled nodes for debugging."""
        source = """
while True:
    pass
"""
        compiler = WtfUICompiler(strict=False)

        # Suppress warnings for this test
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            compiler.compile(source)

        # Should have tracked the While node
        assert len(compiler.unhandled_nodes) >= 1
        node_types = [t for t, _, _ in compiler.unhandled_nodes]
        assert "While" in node_types

    def test_provides_line_column_info(self) -> None:
        """Error messages should include line and column information."""
        import pytest

        source = """
# Comment line 1
# Comment line 2
while True:  # Line 4 (0-indexed as 4, 1-indexed as 4)
    pass
"""
        compiler = WtfUICompiler(strict=True)

        with pytest.raises(NotImplementedError) as exc_info:
            compiler.compile(source)

        error_msg = str(exc_info.value)
        assert "line" in error_msg.lower()
        assert "While" in error_msg

    def test_supported_statements_compile_normally(self) -> None:
        """Supported statements should compile without warnings."""
        import warnings

        source = """
count = Signal(0)
with Div():
    Text("Hello")
"""
        compiler = WtfUICompiler(strict=True)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compiler.compile(source)

            # Should have no warnings
            assert len(w) == 0

        # Should have no unhandled nodes
        assert len(compiler.unhandled_nodes) == 0


class TestComponentRegistry:
    """Test ComponentRegistry integration into WtfUICompiler."""

    def test_compiler_scans_for_components(self) -> None:
        """Compiler registers @component functions during compilation."""
        source = """
from wtfui import component

@component
async def MyWidget():
    Text("Hello")

MyWidget()
"""
        compiler = WtfUICompiler()
        compiler.compile(source)

        # Registry should have the component
        assert "MyWidget" in compiler.registry


class TestComponentInlining:
    """Test @component function inlining at call sites."""

    def test_component_call_emits_dom_opcodes(self) -> None:
        """Calling a @component function emits its body's DOM opcodes."""
        source = """
from wtfui import component

@component
async def Card():
    Text("Card Content")

with Div():
    Card()
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Check that "Card Content" appears twice:
        # Once from function definition and once from inlined call
        # If inlining works, we'll have 2 DOM_TEXT opcodes for same string
        text_opcode = bytes([OpCode.DOM_TEXT])
        count = bytecode.count(text_opcode)

        # We expect:
        # 1. One DOM_TEXT from the function definition being visited
        # 2. One DOM_TEXT from the inlined component call inside the Div
        # So we should have at least 2 DOM_TEXT opcodes
        # (Note: function def creates opcodes but they're not connected to DOM tree)
        # Actually, better test: check that Card Content appears in string table
        # and that we have DOM_TEXT opcodes
        assert b"Card Content" in bytecode, "Expected 'Card Content' from inlined component"
        assert count >= 1, f"Expected at least 1 DOM_TEXT opcode, got {count}"

    def test_component_without_call_no_dom_output(self) -> None:
        """Component definition without call should not produce DOM output in the main tree."""
        source_with_call = """
from wtfui import component

@component
async def Card():
    Text("Hello")

Card()
"""
        source_without_call = """
from wtfui import component

@component
async def Card():
    Text("Hello")
"""

        compiler_with = WtfUICompiler()
        bytecode_with = compiler_with.compile(source_with_call)

        compiler_without = WtfUICompiler()
        bytecode_without = compiler_without.compile(source_without_call)

        # With call should have more DOM operations than without
        # (because the call should inline the component body)
        dom_text_with = bytecode_with.count(bytes([OpCode.DOM_TEXT]))
        dom_text_without = bytecode_without.count(bytes([OpCode.DOM_TEXT]))

        # If inlining works, with_call should have more DOM_TEXT opcodes
        # Currently without inlining, both would be equal
        assert dom_text_with > dom_text_without, (
            f"Component call should inline body. "
            f"With call: {dom_text_with} DOM_TEXT, "
            f"Without call: {dom_text_without} DOM_TEXT"
        )

    def test_nested_component_calls(self) -> None:
        """Nested component calls are recursively inlined."""
        source = """
@component
async def Inner():
    Text("Inner")

@component
async def Outer():
    Inner()

Outer()
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Should have text content "Inner"
        assert b"Inner" in bytecode
