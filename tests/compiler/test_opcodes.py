"""Tests for WtfUIByte opcode definitions."""

from wtfui.web.compiler.opcodes import OpCode


def test_call_opcode_exists():
    """CALL opcode is defined for subroutine calls."""
    assert hasattr(OpCode, "CALL")
    assert OpCode.CALL == 0xC1  # After CALL_INTRINSIC (0xC0)


def test_ret_opcode_exists():
    """RET opcode is defined for subroutine returns."""
    assert hasattr(OpCode, "RET")
    assert OpCode.RET == 0xC2
