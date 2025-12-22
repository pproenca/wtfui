# tests/gatekeepers/test_wtfuibyte_size.py
"""Gatekeeper: WtfUIByte Binary Compactness.

Enforces that the WtfUIByte format achieves the promised 10x size
reduction compared to equivalent JSON representations.

Threshold: Counter component < 100 bytes.
"""

import json
from typing import Any

import pytest

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.writer import BytecodeWriter

# Maximum allowed binary size for counter component
MAX_COUNTER_SIZE = 100

# JSON equivalent for comparison
COUNTER_JSON = {
    "state": {"s0": 0},
    "actions": {
        "a0": [
            ["JMP_GTE", {"ref": "s0"}, 10, "end"],
            ["INC", {"ref": "s0"}],
            "end",
        ]
    },
    "dom": [
        ["TEXT", {"tmpl": "Count: {}", "bind": "s0"}],
        ["BTN", {"text": "Up", "click": "a0"}],
    ],
}


def build_counter_bytecode() -> bytes:
    """Build a Counter component as WtfUIByte binary.

    Equivalent to:
        count = Signal(0)
        def inc(): count.value += 1
        Button("Up", on_click=inc)
    """
    writer = BytecodeWriter()

    # 1. Init Signal ID 0 with value 0.0
    writer.emit_op(OpCode.INIT_SIG_NUM)
    writer.emit_u16(0)  # ID
    writer.emit_f64(0.0)  # Value

    # 2. Jump over the action handler
    writer.emit_op(OpCode.JMP)
    writer.emit_jump_placeholder("render_start")

    # 3. Define increment handler
    writer.mark_label("inc_handler")
    writer.emit_op(OpCode.INC_CONST)
    writer.emit_u16(0)  # Target Signal 0
    writer.emit_f64(1.0)  # Amount
    writer.emit_op(OpCode.HALT)  # Return from handler

    writer.mark_label("render_start")

    # 4. Create Button
    btn_str = writer.alloc_string("button")
    text_str = writer.alloc_string("Up")

    writer.emit_op(OpCode.DOM_CREATE)
    writer.emit_u16(1)  # Node ID 1
    writer.emit_u16(btn_str)

    writer.emit_op(OpCode.DOM_TEXT)
    writer.emit_u16(1)
    writer.emit_u16(text_str)

    # 5. Attach Click Listener
    writer.emit_op(OpCode.DOM_ON_CLICK)
    writer.emit_u16(1)
    writer.emit_jump_placeholder("inc_handler")

    writer.emit_op(OpCode.HALT)

    return writer.finalize()


@pytest.mark.gatekeeper
def test_counter_binary_compactness() -> None:
    """
    Gatekeeper: Binary size must be < 100 bytes.

    JSON equivalent is ~300 bytes. Binary should be ~10x smaller.
    """
    binary = build_counter_bytecode()
    json_size = len(json.dumps(COUNTER_JSON))

    print(f"\n[WtfUIByte Gatekeeper] Binary Size: {len(binary)} bytes")
    print(f"[WtfUIByte Gatekeeper] JSON Size: {json_size} bytes")
    print(f"[WtfUIByte Gatekeeper] Compression Ratio: {json_size / len(binary):.1f}x")

    assert len(binary) < MAX_COUNTER_SIZE, (
        f"Binary too large: {len(binary)} bytes > {MAX_COUNTER_SIZE} bytes"
    )


@pytest.mark.gatekeeper
def test_string_pooling_efficiency() -> None:
    """Verify string pooling prevents duplication."""
    writer = BytecodeWriter()

    # Use same class 50 times
    for _ in range(50):
        writer.alloc_string("p-4")
        writer.alloc_string("bg-blue-500")

    writer.emit_op(OpCode.HALT)
    binary = writer.finalize()

    # Without pooling: 50 * (4 + 11) = 750 bytes for strings alone
    # With pooling: 4 + 11 = 15 bytes for strings
    print(f"\n[WtfUIByte Gatekeeper] Pooled binary: {len(binary)} bytes")

    # Should be much smaller than 100 bytes
    assert len(binary) < 50, "String pooling not working efficiently"


@pytest.mark.gatekeeper
@pytest.mark.benchmark(group="wtfuibyte")
def test_bytecode_assembly_speed(benchmark: Any) -> None:
    """
    Gatekeeper: Bytecode assembly must be fast.

    Threshold: < 1ms for counter component.
    """

    def assemble() -> bytes:
        return build_counter_bytecode()

    result = benchmark(assemble)

    # Verify result is valid
    assert len(result) > 0
    assert result.startswith(b"MYFU")

    avg_time_ms = benchmark.stats.stats.mean * 1000
    print(f"\n[WtfUIByte Gatekeeper] Assembly time: {avg_time_ms:.4f} ms")

    # Should be very fast - < 1ms
    assert avg_time_ms < 1.0, f"Assembly too slow: {avg_time_ms:.4f}ms"
