"""End-to-end tests for FlowByte compilation pipeline."""

import struct

import pytest

from flow.compiler.flowbyte import FlowCompiler, compile_to_flowbyte
from flow.compiler.opcodes import OpCode
from flow.compiler.writer import MAGIC_HEADER


class TestFullPipeline:
    """Test complete compilation pipeline."""

    def test_counter_app_compiles(self) -> None:
        """Full counter app compiles to valid FlowByte."""
        source = """
count = Signal(0)

def increment():
    count.value += 1

with Div():
    Text(f"Count: {count.value}")
    Button("Up", on_click=increment)
"""
        binary = compile_to_flowbyte(source)

        # Verify structure
        assert binary.startswith(MAGIC_HEADER)
        assert binary[-1] == OpCode.HALT

        # Verify size is reasonable (< 200 bytes)
        assert len(binary) < 200, f"Binary too large: {len(binary)} bytes"

    def test_nested_elements_compile(self) -> None:
        """Nested with blocks compile correctly."""
        source = """
with Div():
    with Div():
        Text("Inner")
"""
        binary = compile_to_flowbyte(source)

        # Should have multiple DOM_CREATE opcodes
        dom_create_count = binary.count(bytes([OpCode.DOM_CREATE]))
        assert dom_create_count >= 2

    def test_multiple_signals_compile(self) -> None:
        """Multiple signals get unique IDs."""
        source = """
count = Signal(0)
name = Signal("test")
active = Signal(1)
"""
        compiler = FlowCompiler()
        compiler.compile(source)

        # Verify all signals are registered
        assert len(compiler.signal_map) == 3
        assert set(compiler.signal_map.keys()) == {"count", "name", "active"}

        # IDs should be sequential
        assert compiler.signal_map["count"] == 0
        assert compiler.signal_map["name"] == 1
        assert compiler.signal_map["active"] == 2


class TestBinaryFormat:
    """Test binary format correctness."""

    def test_header_version(self) -> None:
        """Binary includes version information."""
        binary = compile_to_flowbyte("x = Signal(0)")

        # Version bytes are at offset 4-5
        assert binary[4:6] == b"\x00\x01"  # Version 0.1

    def test_string_table_encoding(self) -> None:
        """Strings are properly UTF-8 encoded."""
        source = """
Text("Hello 世界")
"""
        compiler = FlowCompiler()
        binary = compiler.compile(source)

        # Verify UTF-8 string is in binary
        assert "Hello 世界".encode() in binary

    def test_float_encoding(self) -> None:
        """Float values are correctly big-endian encoded."""
        source = "x = Signal(3.14)"
        binary = compile_to_flowbyte(source)

        # Find the float in the binary (after opcode and ID)
        # INIT_SIG_NUM(1) + ID(2) = 3 bytes offset
        header_len = len(MAGIC_HEADER) + 2  # header + string count
        float_offset = header_len + 3

        value = struct.unpack_from("!d", binary, float_offset)[0]
        assert abs(value - 3.14) < 0.001


@pytest.mark.gatekeeper
class TestPerformance:
    """Performance benchmarks for compilation."""

    def test_compilation_speed(self, benchmark) -> None:
        """Compilation should be fast (< 10ms for typical component)."""
        source = """
count = Signal(0)
name = Signal("test")

def increment():
    count.value += 1

with Div():
    with Div():
        Text(f"Count: {count.value}")
    Button("Up", on_click=increment)
"""

        result = benchmark(lambda: compile_to_flowbyte(source))

        assert len(result) > 0

        avg_time_ms = benchmark.stats.stats.mean * 1000
        print(f"\n[FlowByte E2E] Compilation time: {avg_time_ms:.4f} ms")

        assert avg_time_ms < 10.0, f"Compilation too slow: {avg_time_ms}ms"
