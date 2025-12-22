# tests/test_wtfuibyte_writer.py
"""Tests for WtfUIByte BytecodeWriter."""

import struct

import pytest

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.writer import MAGIC_HEADER, BytecodeWriter


class TestBytecodeWriter:
    """Test BytecodeWriter byte emission."""

    def test_emit_opcode(self) -> None:
        """emit_op writes a single byte."""
        writer = BytecodeWriter()
        writer.emit_op(OpCode.HALT)

        assert len(writer.code) == 1
        assert writer.code[0] == 0xFF

    def test_emit_u16(self) -> None:
        """emit_u16 writes big-endian unsigned short."""
        writer = BytecodeWriter()
        writer.emit_u16(0x1234)

        assert len(writer.code) == 2
        assert writer.code[0] == 0x12
        assert writer.code[1] == 0x34

    def test_emit_u32(self) -> None:
        """emit_u32 writes big-endian unsigned int."""
        writer = BytecodeWriter()
        writer.emit_u32(0x12345678)

        assert len(writer.code) == 4
        assert bytes(writer.code) == b"\x12\x34\x56\x78"

    def test_emit_f64(self) -> None:
        """emit_f64 writes big-endian double."""
        writer = BytecodeWriter()
        writer.emit_f64(1.5)

        assert len(writer.code) == 8
        # Verify we can unpack it back
        unpacked = struct.unpack("!d", bytes(writer.code))[0]
        assert unpacked == 1.5


class TestStringPooling:
    """Test string table with deduplication."""

    def test_alloc_string_returns_index(self) -> None:
        """First string gets index 0."""
        writer = BytecodeWriter()
        idx = writer.alloc_string("hello")
        assert idx == 0

    def test_string_pooling_deduplicates(self) -> None:
        """Same string returns same index."""
        writer = BytecodeWriter()
        idx1 = writer.alloc_string("button")
        idx2 = writer.alloc_string("text")
        idx3 = writer.alloc_string("button")  # Duplicate

        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 0  # Same as first "button"

    def test_string_table_overflow(self) -> None:
        """Raise OverflowError when exceeding 64k strings."""
        writer = BytecodeWriter()

        # This would take too long to actually fill, so we mock
        writer._string_map = {f"s{i}": i for i in range(65535)}
        writer._strings = [f"s{i}" for i in range(65535)]

        with pytest.raises(OverflowError, match="64k"):
            writer.alloc_string("one_more")


class TestLabelSystem:
    """Test jump label resolution."""

    def test_mark_label_stores_position(self) -> None:
        """mark_label records current bytecode offset."""
        writer = BytecodeWriter()
        writer.emit_op(OpCode.INIT_SIG_NUM)  # 1 byte
        writer.emit_u16(0)  # 2 bytes
        writer.emit_f64(0.0)  # 8 bytes
        # Total: 11 bytes

        writer.mark_label("handler")
        assert writer._labels["handler"] == 11

    def test_jump_placeholder_filled_on_finalize(self) -> None:
        """Pending jumps get resolved during finalize."""
        writer = BytecodeWriter()

        # Emit jump with placeholder
        writer.emit_op(OpCode.JMP)
        writer.emit_jump_placeholder("target")

        # Mark target label
        writer.mark_label("target")
        writer.emit_op(OpCode.HALT)

        binary = writer.finalize()

        # Parse the binary to verify
        # Header + string table (2 bytes for count=0) + code
        header_len = len(MAGIC_HEADER)
        str_table_len = 2  # Just the count (0)
        code_start = header_len + str_table_len

        # JMP opcode at code_start, then u32 address
        jmp_addr = struct.unpack_from("!I", binary, code_start + 1)[0]

        # Target should point to HALT (after JMP opcode + u32)
        expected_addr = 5  # 1 byte JMP + 4 bytes address
        assert jmp_addr == expected_addr


class TestFinalize:
    """Test binary assembly."""

    def test_finalize_includes_magic_header(self) -> None:
        """Binary starts with MYFU magic header."""
        writer = BytecodeWriter()
        writer.emit_op(OpCode.HALT)

        binary = writer.finalize()

        assert binary.startswith(MAGIC_HEADER)

    def test_finalize_includes_string_table(self) -> None:
        """String table is encoded in binary."""
        writer = BytecodeWriter()
        writer.alloc_string("hello")
        writer.emit_op(OpCode.HALT)

        binary = writer.finalize()

        # After header, we have [count: u16][len: u16][bytes...]
        header_len = len(MAGIC_HEADER)
        count = struct.unpack_from("!H", binary, header_len)[0]
        assert count == 1

        str_len = struct.unpack_from("!H", binary, header_len + 2)[0]
        assert str_len == 5  # "hello"

        str_bytes = binary[header_len + 4 : header_len + 4 + str_len]
        assert str_bytes == b"hello"

    def test_undefined_label_raises(self) -> None:
        """Referencing undefined label raises ValueError."""
        writer = BytecodeWriter()
        writer.emit_op(OpCode.JMP)
        writer.emit_jump_placeholder("undefined_label")

        with pytest.raises(ValueError, match="Undefined label"):
            writer.finalize()
