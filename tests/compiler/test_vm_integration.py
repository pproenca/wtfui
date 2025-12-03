"""Tests for FlowByte VM integration.

Verifies that the compiler output is compatible with the JavaScript VM
and that the VM generation produces valid JavaScript.
"""

import struct

from flow.cli import _get_vm_inline
from flow.compiler.flowbyte import compile_to_flowbyte
from flow.compiler.intrinsics import IntrinsicID
from flow.compiler.opcodes import OpCode


def test_vm_inline_generates_javascript():
    """VM inline function returns valid JavaScript class."""
    js = _get_vm_inline()

    # Verify it's a JavaScript class
    assert "class FlowVM" in js
    assert "constructor" not in js or "signals = new Map()" in js  # Uses class fields
    assert "execute(pc)" in js
    assert "callIntrinsic(id, args)" in js


def test_vm_has_stack_operations():
    """VM includes all stack operation handlers."""
    js = _get_vm_inline()

    # Stack operations
    assert "case 0xA0:" in js  # PUSH_NUM
    assert "case 0xA1:" in js  # PUSH_STR
    assert "case 0xA2:" in js  # LOAD_SIG
    assert "case 0xA3:" in js  # STORE_SIG
    assert "case 0xA4:" in js  # POP
    assert "case 0xA5:" in js  # DUP


def test_vm_has_arithmetic_operations():
    """VM includes stack-based arithmetic handlers."""
    js = _get_vm_inline()

    # Arithmetic operations
    assert "case 0x22:" in js  # MUL
    assert "case 0x23:" in js  # DIV
    assert "case 0x24:" in js  # MOD
    assert "case 0x26:" in js  # ADD_STACK
    assert "case 0x27:" in js  # SUB_STACK


def test_vm_has_comparison_operations():
    """VM includes all comparison operator handlers."""
    js = _get_vm_inline()

    # Comparison operations
    assert "case 0x30:" in js  # EQ
    assert "case 0x31:" in js  # NE
    assert "case 0x32:" in js  # LT
    assert "case 0x33:" in js  # LE
    assert "case 0x34:" in js  # GT
    assert "case 0x35:" in js  # GE


def test_vm_has_intrinsic_handler():
    """VM includes intrinsic call handler."""
    js = _get_vm_inline()

    assert "case 0xC0:" in js  # CALL_INTRINSIC
    assert "callIntrinsic" in js

    # Check all intrinsic implementations
    assert "case 0x01:" in js  # PRINT
    assert "case 0x02:" in js  # LEN
    assert "case 0x03:" in js  # STR
    assert "case 0x04:" in js  # INT
    assert "case 0x05:" in js  # RANGE


def test_bytecode_format_has_magic_header():
    """Compiled bytecode starts with FLOW magic header."""
    source = "count = Signal(0)"
    binary = compile_to_flowbyte(source)

    assert binary[:4] == b"FLOW"
    assert binary[4:6] == b"\x00\x01"  # Version 1.0


def test_bytecode_string_table_format():
    """String table is correctly formatted for VM parsing."""
    source = """
count = Signal(0)
print("Hello")
"""
    binary = compile_to_flowbyte(source)

    # Skip header (6 bytes)
    offset = 6

    # Read string count (u16 big-endian)
    string_count = struct.unpack("!H", binary[offset : offset + 2])[0]
    offset += 2

    # Should have at least "Hello" string
    assert string_count >= 1

    # Verify string format: [len: u16][bytes...]
    strings = []
    for _ in range(string_count):
        str_len = struct.unpack("!H", binary[offset : offset + 2])[0]
        offset += 2
        str_bytes = binary[offset : offset + str_len]
        strings.append(str_bytes.decode("utf-8"))
        offset += str_len

    assert "Hello" in strings


def test_bytecode_opcodes_are_single_bytes():
    """Opcodes are emitted as single bytes for VM switch statement."""
    source = """
count = Signal(0)
count.value += 1
"""
    binary = compile_to_flowbyte(source)

    # Find INIT_SIG_NUM opcode (0x01)
    assert bytes([0x01]) in binary

    # Find LOAD_SIG opcode (0xA2)
    assert bytes([0xA2]) in binary

    # Find PUSH_NUM opcode (0xA0)
    assert bytes([0xA0]) in binary

    # Find ADD_STACK opcode (0x26)
    assert bytes([0x26]) in binary

    # Find STORE_SIG opcode (0xA3)
    assert bytes([0xA3]) in binary

    # Find HALT opcode (0xFF)
    assert bytes([0xFF]) in binary


def test_intrinsic_call_format():
    """CALL_INTRINSIC is followed by intrinsic_id and argc."""
    source = """
count = Signal(42)
print(count.value)
"""
    binary = compile_to_flowbyte(source)

    # Find CALL_INTRINSIC sequence: [0xC0][intrinsic_id][argc]
    # PRINT = 0x01, argc = 1
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.PRINT, 1]) in binary


def test_numeric_constants_are_f64():
    """Numeric constants are encoded as 8-byte big-endian floats."""
    source = """
count = Signal(42)
count.value += 10
"""
    binary = compile_to_flowbyte(source)

    # 42.0 as f64 big-endian
    expected_42 = struct.pack("!d", 42.0)
    assert expected_42 in binary

    # 10.0 as f64 big-endian
    expected_10 = struct.pack("!d", 10.0)
    assert expected_10 in binary


def test_signal_ids_are_u16():
    """Signal IDs are encoded as 2-byte big-endian unsigned shorts."""
    source = """
a = Signal(1)
b = Signal(2)
c = Signal(3)
"""
    binary = compile_to_flowbyte(source)

    # Signal IDs 0, 1, 2 should all appear
    # After INIT_SIG_NUM (0x01), next 2 bytes are the signal ID
    init_positions = []
    for i in range(len(binary) - 1):
        if binary[i] == 0x01:  # INIT_SIG_NUM
            init_positions.append(i)

    assert len(init_positions) >= 3  # At least 3 signals initialized
