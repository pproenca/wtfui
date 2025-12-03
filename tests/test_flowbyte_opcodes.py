"""Tests for FlowByte opcode definitions."""

from flow.compiler.opcodes import OpCode


class TestOpcodeDefinitions:
    """Verify opcode values are unique and correctly defined."""

    def test_opcode_values_are_unique(self) -> None:
        """Each opcode must have a unique byte value."""
        values = [op.value for op in OpCode]
        assert len(values) == len(set(values)), "Duplicate opcode values found"

    def test_opcode_ranges(self) -> None:
        """Verify opcodes fall within their designated ranges."""
        # Signals: 0x00-0x1F
        assert 0x00 <= OpCode.INIT_SIG_NUM.value <= 0x1F
        assert 0x00 <= OpCode.INIT_SIG_STR.value <= 0x1F
        assert 0x00 <= OpCode.SET_SIG_NUM.value <= 0x1F

        # Arithmetic: 0x20-0x3F
        assert 0x20 <= OpCode.ADD.value <= 0x3F
        assert 0x20 <= OpCode.SUB.value <= 0x3F
        assert 0x20 <= OpCode.INC_CONST.value <= 0x3F

        # Control flow: 0x40-0x5F
        assert 0x40 <= OpCode.JMP_TRUE.value <= 0x5F
        assert 0x40 <= OpCode.JMP_FALSE.value <= 0x5F
        assert 0x40 <= OpCode.JMP.value <= 0x5F

        # DOM: 0x60-0x8F
        assert 0x60 <= OpCode.DOM_CREATE.value <= 0x8F
        assert 0x60 <= OpCode.DOM_APPEND.value <= 0x8F
        assert 0x60 <= OpCode.DOM_TEXT.value <= 0x8F
        assert 0x60 <= OpCode.DOM_BIND_TEXT.value <= 0x8F
        assert 0x60 <= OpCode.DOM_ON_CLICK.value <= 0x8F
        assert 0x60 <= OpCode.DOM_ATTR_CLASS.value <= 0x8F

        # Network: 0x90-0xFE
        assert 0x90 <= OpCode.RPC_CALL.value <= 0xFE

        # Special: 0xFF
        assert OpCode.HALT.value == 0xFF

    def test_opcode_is_int_enum(self) -> None:
        """OpCode should be an IntEnum for byte packing."""
        assert isinstance(OpCode.HALT.value, int)
        assert OpCode.HALT.value == 0xFF
