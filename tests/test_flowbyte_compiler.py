"""Tests for FlowByte AST Compiler."""

import struct

from flow.compiler.flowbyte import FlowCompiler
from flow.compiler.opcodes import OpCode
from flow.compiler.writer import MAGIC_HEADER


class TestSignalCompilation:
    """Test Signal initialization compilation."""

    def test_compile_signal_init_numeric(self) -> None:
        """Signal(0) compiles to INIT_SIG_NUM opcode."""
        source = """
count = Signal(0)
"""
        compiler = FlowCompiler()
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
        compiler = FlowCompiler()
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
        compiler = FlowCompiler()
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
        compiler = FlowCompiler()
        binary = compiler.compile(source)

        # Find DOM_CREATE opcode
        assert OpCode.DOM_CREATE in binary

    def test_compile_text_element(self) -> None:
        """Text("hello") compiles to DOM_CREATE + DOM_TEXT."""
        source = """
with Div():
    Text("hello")
"""
        compiler = FlowCompiler()
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
        compiler = FlowCompiler()
        binary = compiler.compile(source)

        # Should have DOM_ON_CLICK opcode
        assert OpCode.DOM_ON_CLICK in binary

        # "Up" should be in string table
        assert "Up" in compiler.writer._string_map


class TestCompilerOutput:
    """Test overall compiler output."""

    def test_output_starts_with_magic_header(self) -> None:
        """All output starts with FLOW magic header."""
        source = "x = Signal(0)"
        compiler = FlowCompiler()
        binary = compiler.compile(source)

        assert binary.startswith(MAGIC_HEADER)

    def test_output_ends_with_halt(self) -> None:
        """All output ends with HALT opcode."""
        source = "x = Signal(0)"
        compiler = FlowCompiler()
        binary = compiler.compile(source)

        assert binary[-1] == OpCode.HALT
