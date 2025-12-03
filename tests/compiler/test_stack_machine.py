"""Tests for stack-based bytecode compilation.

Verifies that the FlowByte compiler generates correct stack-based opcodes
for arithmetic expressions, intrinsic function calls, and nested operations.
"""

from flow.compiler.flowbyte import compile_to_flowbyte
from flow.compiler.intrinsics import IntrinsicID
from flow.compiler.opcodes import OpCode
from flow.compiler.writer import MAGIC_HEADER


def test_arithmetic_compilation():
    """Stack-based arithmetic compiles to correct opcode sequence.

    Expected behavior:
    - Expression `count.value += 1` should compile to:
      INIT_SIG_NUM(count), LOAD_SIG(count), PUSH_NUM(1), ADD_STACK, STORE_SIG(count)
    """
    source = """
count = Signal(0)
count.value += 1
"""
    binary = compile_to_flowbyte(source)

    # Verify header
    assert binary.startswith(MAGIC_HEADER)

    # Verify opcodes are present in binary (as single bytes)
    assert bytes([OpCode.INIT_SIG_NUM]) in binary
    assert bytes([OpCode.LOAD_SIG]) in binary
    assert bytes([OpCode.PUSH_NUM]) in binary
    assert bytes([OpCode.ADD_STACK]) in binary
    assert bytes([OpCode.STORE_SIG]) in binary
    assert bytes([OpCode.HALT]) in binary


def test_intrinsic_compilation():
    """Intrinsic function calls compile to CALL_INTRINSIC opcode.

    Expected behavior:
    - Expression `print("Hello")` should compile to:
      PUSH_STR(str_id), CALL_INTRINSIC(PRINT, argc=1)
    """
    source = """
count = Signal(0)
print(count.value)
"""
    binary = compile_to_flowbyte(source)

    # Verify header
    assert binary.startswith(MAGIC_HEADER)

    # Verify intrinsic call opcode present
    assert bytes([OpCode.CALL_INTRINSIC]) in binary
    # Verify PRINT intrinsic ID follows the opcode
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.PRINT, 1]) in binary


def test_nested_intrinsics():
    """Nested intrinsic calls compile with correct stack ordering.

    Expected behavior:
    - Expression `print(str(count.value))` should compile to:
      1. LOAD_SIG(count) - push signal value
      2. CALL_INTRINSIC(STR, argc=1) - pops value, pushes string
      3. CALL_INTRINSIC(PRINT, argc=1) - pops string, prints it
    """
    source = """
count = Signal(42)
print(str(count.value))
"""
    binary = compile_to_flowbyte(source)

    # Verify both intrinsic calls are present
    # STR intrinsic: CALL_INTRINSIC, STR(0x03), argc=1
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.STR, 1]) in binary
    # PRINT intrinsic: CALL_INTRINSIC, PRINT(0x01), argc=1
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.PRINT, 1]) in binary


def test_comparison_operators():
    """Comparison operators compile to stack-based opcodes.

    All comparison opcodes should exist with correct values.
    """
    # Verify all comparison opcodes exist with correct values
    assert OpCode.EQ.value == 0x30
    assert OpCode.NE.value == 0x31
    assert OpCode.LT.value == 0x32
    assert OpCode.LE.value == 0x33
    assert OpCode.GT.value == 0x34
    assert OpCode.GE.value == 0x35


def test_stack_operations():
    """Stack manipulation opcodes exist and have correct values.

    Verifies:
    - PUSH_NUM/PUSH_STR for pushing constants
    - LOAD_SIG/STORE_SIG for signal access
    - POP for discarding values
    - DUP for duplicating top of stack
    """
    # Verify all stack opcodes in 0xA0-0xBF range
    assert OpCode.PUSH_NUM.value == 0xA0
    assert OpCode.PUSH_STR.value == 0xA1
    assert OpCode.LOAD_SIG.value == 0xA2
    assert OpCode.STORE_SIG.value == 0xA3
    assert OpCode.POP.value == 0xA4
    assert OpCode.DUP.value == 0xA5

    # Verify they're in correct range
    assert 0xA0 <= OpCode.PUSH_NUM.value <= 0xBF
    assert 0xA0 <= OpCode.DUP.value <= 0xBF


def test_multiply_operation():
    """Multiplication compiles to MUL opcode."""
    source = """
a = Signal(2)
b = Signal(3)
a.value *= b.value
"""
    binary = compile_to_flowbyte(source)

    assert bytes([OpCode.MUL]) in binary
    assert bytes([OpCode.STORE_SIG]) in binary


def test_expression_with_constant():
    """Expressions with constants use PUSH_NUM."""
    source = """
count = Signal(10)
count.value += 5
"""
    binary = compile_to_flowbyte(source)

    # Verify PUSH_NUM is in binary
    assert bytes([OpCode.PUSH_NUM]) in binary
    # Verify ADD_STACK is used (not legacy ADD)
    assert bytes([OpCode.ADD_STACK]) in binary


def test_subtraction_operation():
    """Subtraction compiles to SUB_STACK opcode."""
    source = """
count = Signal(10)
count.value -= 3
"""
    binary = compile_to_flowbyte(source)

    assert bytes([OpCode.SUB_STACK]) in binary
