# tests/compiler/test_wtfuibyte_optimizer.py
"""Tests that WtfUICompiler runs optimizer passes before codegen."""

import struct

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.wtfuibyte import WtfUICompiler

# WtfUIByte binary layout:
# - HEADER: 6 bytes (b"MYFU" + 2-byte version)
# - STRING_TABLE: 2 bytes count (u16 BE) + strings
# - CODE: instructions
HEADER_SIZE = 6
STRING_TABLE_EMPTY_SIZE = 2  # Just the count (0) when no strings


class TestWtfUICompilerOptimization:
    """Tests that optimizer is integrated into compile pipeline."""

    def test_constant_folding_in_compile(self) -> None:
        """Constant expressions are folded before bytecode generation.

        The optimizer should fold `2 + 3` to `5` at compile time,
        resulting in a single INIT_SIG_NUM instruction with value 5.0.
        """
        compiler = WtfUICompiler()

        # Source with constant expression
        source = """
count = Signal(2 + 3)
"""
        bytecode = compiler.compile(source)

        # Verify bytecode contains the folded value 5.0
        # INIT_SIG_NUM emits: opcode (1) + signal_id (2 BE) + value (8 BE) = 11 bytes
        assert len(bytecode) > 0

        # Find INIT_SIG_NUM opcode and verify value is 5.0
        # Skip header (6) + empty string table (2) = offset 8
        offset = HEADER_SIZE + STRING_TABLE_EMPTY_SIZE
        found_signal_init = False

        while offset < len(bytecode) - 1:
            op = bytecode[offset]
            if op == OpCode.INIT_SIG_NUM.value:
                # Skip opcode (1) + signal_id (2 BE), read float64 value (8 BE)
                # WtfUIByte uses big-endian (network byte order)
                value = struct.unpack("!d", bytecode[offset + 3 : offset + 11])[0]
                assert value == 5.0, f"Expected folded value 5.0, got {value}"
                found_signal_init = True
                break
            offset += 1

        assert found_signal_init, "Should emit INIT_SIG_NUM for Signal initialization"

    def test_dead_code_elimination_in_compile(self) -> None:
        """Dead code branches are eliminated before bytecode generation.

        The optimizer should remove `if False:` branches entirely,
        resulting in no INIT_SIG_NUM for the dead branch.
        """
        compiler = WtfUICompiler()

        source = """
if False:
    x = Signal(1)
y = Signal(2)
"""
        bytecode = compiler.compile(source)

        # Should only have INIT_SIG_NUM for y=2, not for x=1
        # Skip header (6) + empty string table (2) = offset 8
        offset = HEADER_SIZE + STRING_TABLE_EMPTY_SIZE
        signal_values = []

        while offset < len(bytecode) - 11:
            op = bytecode[offset]
            if op == OpCode.INIT_SIG_NUM.value:
                # WtfUIByte uses big-endian (network byte order)
                value = struct.unpack("!d", bytecode[offset + 3 : offset + 11])[0]
                signal_values.append(value)
                offset += 11
            else:
                offset += 1

        # Only y = Signal(2) should be emitted
        assert 2.0 in signal_values, "Should emit Signal(2)"
        assert 1.0 not in signal_values, "Should NOT emit Signal(1) from dead branch"
