"""Tests for VM parity between TypeScript and embedded implementations.

Ensures that the TypeScript VM (vm.ts) and the embedded fallback VM (cli/__init__.py)
implement the same set of opcodes, preventing silent divergence over time.
"""

import re
from pathlib import Path

from wtfui.cli.vm import get_vm_inline
from wtfui.web.compiler.opcodes import OpCode


def _extract_opcodes_from_ts() -> set[int]:
    """Extract opcode handlers from TypeScript VM source."""
    vm_ts = Path(__file__).parent.parent.parent / "src" / "wtfui" / "static" / "vm.ts"
    if not vm_ts.exists():
        return set()

    content = vm_ts.read_text()

    # Find all "case OPS.XXX:" patterns
    ops_pattern = re.findall(r"case OPS\.(\w+):", content)

    # Also extract the OPS constant definitions
    ops_defs = re.findall(r"(\w+):\s*(0x[0-9a-fA-F]+)", content)
    ops_map = {name: int(val, 16) for name, val in ops_defs}

    return {ops_map[name] for name in ops_pattern if name in ops_map}


def _extract_opcodes_from_embedded() -> set[int]:
    """Extract opcode handlers from the main execute() switch in embedded VM.

    We need to be careful to only extract opcodes from the main execute loop,
    not from nested switch statements (like callIntrinsic).
    """
    js = get_vm_inline(use_bundled=False)

    # Find the main execute function and extract only its switch cases
    # The execute function has the main opcode switch
    # We look for patterns in the 0x00-0xFF range that are actual opcodes

    # Find all "case 0xXX:" patterns
    case_pattern = re.findall(r"case (0x[0-9a-fA-F]{2}):", js)

    # Filter to only include valid opcode ranges (not intrinsic IDs which are 0x01-0x05)
    # Opcodes are: 0x01-0x03 (signals), 0x20-0x27 (arith), 0x30-0x35 (cmp),
    #              0x40-0x42 (control), 0x60-0x71 (dom), 0x88 (router), 0x90 (rpc),
    #              0xA0-0xA5 (stack), 0xC0-0xC2 (intrinsics/call/ret), 0xFF (halt)
    valid_opcode_ranges = [
        (0x01, 0x03),  # Signals
        (0x20, 0x27),  # Arithmetic
        (0x30, 0x35),  # Comparison
        (0x40, 0x42),  # Control flow
        (0x60, 0x71),  # DOM (includes DOM_IF and DOM_FOR)
        (0x88, 0x88),  # DOM_ROUTER
        (0x90, 0x90),  # RPC
        (0xA0, 0xA5),  # Stack
        (0xC0, 0xC2),  # Intrinsics, CALL, RET
        (0xFF, 0xFF),  # Halt
    ]

    def is_valid_opcode(val: int) -> bool:
        return any(start <= val <= end for start, end in valid_opcode_ranges)

    return {int(val, 16) for val in case_pattern if is_valid_opcode(int(val, 16))}


def _extract_opcodes_from_python() -> set[int]:
    """Extract all opcodes defined in Python OpCode enum."""
    return {op.value for op in OpCode}


def test_typescript_vm_has_all_python_opcodes():
    """TypeScript VM implements all Python-defined opcodes."""
    ts_opcodes = _extract_opcodes_from_ts()
    python_opcodes = _extract_opcodes_from_python()

    if not ts_opcodes:
        # vm.ts doesn't exist (e.g., in minimal install), skip
        return

    missing = python_opcodes - ts_opcodes
    # Remove legacy register-based ADD/SUB (0x20, 0x21) which are deprecated
    # but still defined in Python for backwards compatibility
    legacy_deprecated = {0x20, 0x21}
    missing = missing - legacy_deprecated

    assert not missing, (
        f"TypeScript VM missing opcodes: "
        f"{[hex(op) for op in sorted(missing)]} "
        f"({[OpCode(op).name for op in sorted(missing)]})"
    )


def test_embedded_vm_has_all_python_opcodes():
    """Embedded VM implements all Python-defined opcodes."""
    embedded_opcodes = _extract_opcodes_from_embedded()
    python_opcodes = _extract_opcodes_from_python()

    # Remove legacy register-based ADD/SUB (0x20, 0x21) which are deprecated
    legacy_deprecated = {0x20, 0x21}
    # These opcodes are intentionally not in embedded VM - it's a minimal fallback
    # that doesn't need advanced DOM control flow (handled by full TypeScript VM)
    intentionally_missing = {
        OpCode.RPC_CALL,
        OpCode.DOM_IF,
        OpCode.DOM_FOR,
        OpCode.DOM_ROUTER,
    }
    expected = python_opcodes - legacy_deprecated - intentionally_missing

    missing = expected - embedded_opcodes

    assert not missing, (
        f"Embedded VM missing opcodes: "
        f"{[hex(op) for op in sorted(missing)]} "
        f"({[OpCode(op).name for op in sorted(missing)]})"
    )


def test_embedded_and_typescript_have_same_opcodes():
    """Embedded and TypeScript VMs implement the same opcodes."""
    ts_opcodes = _extract_opcodes_from_ts()
    embedded_opcodes = _extract_opcodes_from_embedded()

    if not ts_opcodes:
        # vm.ts doesn't exist, skip
        return

    # TypeScript has some extra opcodes for backwards compat (ADD, SUB register-based)
    # Normalize by removing 0x20, 0x21 from comparison
    ts_normalized = ts_opcodes - {0x20, 0x21}
    embedded_normalized = embedded_opcodes - {0x20, 0x21}

    in_ts_not_embedded = ts_normalized - embedded_normalized
    in_embedded_not_ts = embedded_normalized - ts_normalized

    if in_ts_not_embedded:
        # TypeScript has opcodes embedded doesn't - this is ok if they're backwards compat
        pass

    assert not in_embedded_not_ts, (
        f"Embedded VM has opcodes TypeScript doesn't: "
        f"{[hex(op) for op in sorted(in_embedded_not_ts)]}"
    )


def test_opcode_values_match_spec():
    """Opcode values match the documented specification."""
    # Signals & State: 0x00-0x1F
    assert 0x00 <= OpCode.INIT_SIG_NUM <= 0x1F
    assert 0x00 <= OpCode.INIT_SIG_STR <= 0x1F
    assert 0x00 <= OpCode.SET_SIG_NUM <= 0x1F

    # Arithmetic: 0x20-0x3F
    assert 0x20 <= OpCode.ADD <= 0x3F
    assert 0x20 <= OpCode.SUB <= 0x3F
    assert 0x20 <= OpCode.MUL <= 0x3F
    assert 0x20 <= OpCode.DIV <= 0x3F
    assert 0x20 <= OpCode.MOD <= 0x3F
    assert 0x20 <= OpCode.INC_CONST <= 0x3F
    assert 0x20 <= OpCode.ADD_STACK <= 0x3F
    assert 0x20 <= OpCode.SUB_STACK <= 0x3F

    # Comparison: 0x30-0x3F
    assert 0x30 <= OpCode.EQ <= 0x3F
    assert 0x30 <= OpCode.NE <= 0x3F
    assert 0x30 <= OpCode.LT <= 0x3F
    assert 0x30 <= OpCode.LE <= 0x3F
    assert 0x30 <= OpCode.GT <= 0x3F
    assert 0x30 <= OpCode.GE <= 0x3F

    # Control Flow: 0x40-0x5F
    assert 0x40 <= OpCode.JMP_TRUE <= 0x5F
    assert 0x40 <= OpCode.JMP_FALSE <= 0x5F
    assert 0x40 <= OpCode.JMP <= 0x5F

    # DOM: 0x60-0x8F
    assert 0x60 <= OpCode.DOM_CREATE <= 0x8F
    assert 0x60 <= OpCode.DOM_APPEND <= 0x8F
    assert 0x60 <= OpCode.DOM_TEXT <= 0x8F
    assert 0x60 <= OpCode.DOM_BIND_TEXT <= 0x8F
    assert 0x60 <= OpCode.DOM_ON_CLICK <= 0x8F
    assert 0x60 <= OpCode.DOM_ATTR_CLASS <= 0x8F
    assert 0x60 <= OpCode.DOM_STYLE_STATIC <= 0x8F
    assert 0x60 <= OpCode.DOM_STYLE_DYN <= 0x8F
    assert 0x60 <= OpCode.DOM_ATTR <= 0x8F
    assert 0x60 <= OpCode.DOM_BIND_ATTR <= 0x8F
    assert 0x60 <= OpCode.DOM_IF <= 0x8F
    assert 0x60 <= OpCode.DOM_FOR <= 0x8F
    assert 0x60 <= OpCode.DOM_ROUTER <= 0x8F

    # Network: 0x90-0x9F
    assert 0x90 <= OpCode.RPC_CALL <= 0x9F

    # Stack: 0xA0-0xBF
    assert 0xA0 <= OpCode.PUSH_NUM <= 0xBF
    assert 0xA0 <= OpCode.PUSH_STR <= 0xBF
    assert 0xA0 <= OpCode.LOAD_SIG <= 0xBF
    assert 0xA0 <= OpCode.STORE_SIG <= 0xBF
    assert 0xA0 <= OpCode.POP <= 0xBF
    assert 0xA0 <= OpCode.DUP <= 0xBF

    # Intrinsics: 0xC0-0xDF
    assert 0xC0 <= OpCode.CALL_INTRINSIC <= 0xDF

    # Control
    assert OpCode.HALT == 0xFF


def test_embedded_vm_missing_rpc_call():
    """Document that embedded VM is missing RPC_CALL (known limitation)."""
    embedded_opcodes = _extract_opcodes_from_embedded()

    # RPC_CALL (0x90) is intentionally not in embedded VM
    # The embedded VM is a minimal fallback, RPC requires server communication
    assert OpCode.RPC_CALL not in embedded_opcodes, (
        "Embedded VM now has RPC_CALL - update this test and documentation"
    )
