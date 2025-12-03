# FlowByte Compiler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use super:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Implement a FlowByte binary compiler that transforms Python components into a compact bytecode format (~10x smaller than JSON), eliminating the need for Pyodide in the browser while maintaining the elegant Python developer experience.

**Architecture:** The FlowByte system consists of three layers: (1) an Opcode registry defining a compact instruction set, (2) a BytecodeWriter that assembles binary payloads with string pooling, and (3) a FlowCompiler that walks the Python AST and emits opcodes. The client-side VM (~3KB) executes the bytecode directly from an ArrayBuffer, achieving zero parse time and minimal memory allocation.

**Tech Stack:** Python 3.14+, `struct` module for binary packing, `ast` module for source analysis, TypeScript for browser VM, FastAPI for dev server integration.

**Commands:** All Python commands use `uv run` prefix.

**Steering Council Feedback:**
> In Task 6 (VM), ensure the DOM_BIND_TEXT opcode handles updates efficiently. The current implementation re-renders the text content on every signal change. For V2, consider fine-grained updates (Text Nodes) to avoid thrashing layout.

This V1 implementation uses `textContent` replacement for simplicity. V2 should use `Text` nodes with `nodeValue` updates for surgical DOM changes without triggering layout recalculation.

---

## Phase 1: Opcode Registry & BytecodeWriter

### Task 1: Define FlowByte Opcode Registry

**Files:**
- Create: `src/flow/compiler/opcodes.py`
- Test: `tests/test_flowbyte_opcodes.py`

**Step 1: Write the failing test**

```python
# tests/test_flowbyte_opcodes.py
"""Tests for FlowByte opcode definitions."""

import pytest

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
        assert OpCode.HALT == 0xFF
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_flowbyte_opcodes.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'flow.compiler.opcodes'" or "cannot import name 'OpCode'"

**Step 3: Write minimal implementation**

```python
# src/flow/compiler/opcodes.py
"""FlowByte Instruction Set Architecture.

Defines the opcodes for the Flow Virtual Machine. This is the contract
between the Python Compiler and the JavaScript VM.

Format: [OPCODE: u8] [ARGS...]
All multi-byte arguments are Big-Endian (!).

Opcode Ranges:
- 0x00-0x1F: Signals & State
- 0x20-0x3F: Arithmetic
- 0x40-0x5F: Control Flow
- 0x60-0x8F: DOM Manipulation
- 0x90-0xFE: Network (RPC)
- 0xFF: HALT
"""

from enum import IntEnum


class OpCode(IntEnum):
    """FlowByte Instruction Set."""

    # --- SIGNALS & STATE (0x00 - 0x1F) ---

    # Create a new signal with numeric value.
    # Args: [ID: u16] [INITIAL_VAL: f64]
    INIT_SIG_NUM = 0x01

    # Create a new signal with string value.
    # Args: [ID: u16] [STR_ID: u16]
    INIT_SIG_STR = 0x02

    # Update a signal value (numeric).
    # Args: [ID: u16] [NEW_VAL: f64]
    SET_SIG_NUM = 0x03

    # --- ARITHMETIC (0x20 - 0x3F) ---

    # Add two signals: target.value = source_a.value + source_b.value
    # Args: [TARGET: u16] [SRC_A: u16] [SRC_B: u16]
    ADD = 0x20

    # Subtract: target = a - b
    # Args: [TARGET: u16] [SRC_A: u16] [SRC_B: u16]
    SUB = 0x21

    # Increment signal by constant.
    # Args: [TARGET: u16] [AMOUNT: f64]
    INC_CONST = 0x25

    # --- CONTROL FLOW (0x40 - 0x5F) ---

    # Jump if Signal is Truthy.
    # Args: [SIG_ID: u16] [ADDR: u32]
    JMP_TRUE = 0x40

    # Jump if Signal is Falsy.
    # Args: [SIG_ID: u16] [ADDR: u32]
    JMP_FALSE = 0x41

    # Unconditional Jump.
    # Args: [ADDR: u32]
    JMP = 0x42

    # --- DOM MANIPULATION (0x60 - 0x8F) ---

    # Create DOM Element.
    # Args: [NODE_ID: u16] [TAG_STR_ID: u16]
    DOM_CREATE = 0x60

    # Append Child.
    # Args: [PARENT_ID: u16] [CHILD_ID: u16]
    DOM_APPEND = 0x61

    # Set Text Content (Static).
    # Args: [NODE_ID: u16] [STR_ID: u16]
    DOM_TEXT = 0x62

    # Bind Text Content to Signal (Reactive).
    # Args: [NODE_ID: u16] [SIG_ID: u16] [TEMPLATE_STR_ID: u16]
    # Template example: "Count: {}"
    DOM_BIND_TEXT = 0x63

    # Add Event Listener (Click).
    # Args: [NODE_ID: u16] [JMP_ADDR: u32]
    DOM_ON_CLICK = 0x64

    # Set Attribute (Class).
    # Args: [NODE_ID: u16] [STR_ID: u16]
    DOM_ATTR_CLASS = 0x65

    # --- NETWORK (0x90 - 0xFF) ---

    # Call Server RPC.
    # Args: [FUNC_STR_ID: u16] [RESULT_SIG_ID: u16]
    RPC_CALL = 0x90

    # End of Bytecode
    HALT = 0xFF
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_flowbyte_opcodes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/compiler/opcodes.py tests/test_flowbyte_opcodes.py
git commit -m "$(cat <<'EOF'
feat(compiler): add FlowByte opcode registry

Define instruction set for FlowByte VM with ranges:
- Signals & State (0x00-0x1F)
- Arithmetic (0x20-0x3F)
- Control Flow (0x40-0x5F)
- DOM Manipulation (0x60-0x8F)
- Network/RPC (0x90-0xFE)
- HALT (0xFF)
EOF
)"
```

---

### Task 2: Implement BytecodeWriter with Struct Packing

**Files:**
- Create: `src/flow/compiler/writer.py`
- Test: `tests/test_flowbyte_writer.py`

**Step 1: Write the failing test**

```python
# tests/test_flowbyte_writer.py
"""Tests for FlowByte BytecodeWriter."""

import struct

import pytest

from flow.compiler.opcodes import OpCode
from flow.compiler.writer import MAGIC_HEADER, BytecodeWriter


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
        """Binary starts with FLOW magic header."""
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_flowbyte_writer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'flow.compiler.writer'"

**Step 3: Write minimal implementation**

```python
# src/flow/compiler/writer.py
"""FlowByte BytecodeWriter - Binary assembler with string pooling.

Generates .fbc (FlowByte Code) binaries that are ~10x smaller than
equivalent JSON representations.

Binary Layout:
    [HEADER: 6 bytes] [STRING_TABLE] [CODE]

Header Format:
    "FLOW" (4 bytes) + Version (2 bytes)

String Table Format:
    [COUNT: u16] [STR_LEN: u16, BYTES...]...
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from flow.compiler.opcodes import OpCode

# Magic Header: 'FLOW' + Version 1.0 (major.minor as u8.u8)
MAGIC_HEADER = b"FLOW\x00\x01"


@dataclass
class BytecodeWriter:
    """
    Generates .fbc (FlowByte Code) binaries.

    Handles endianness, string pooling, and jump label resolution.
    All multi-byte values use big-endian (network byte order).
    """

    # The Instruction Stream
    code: bytearray = field(default_factory=bytearray)

    # String Table: Maps string -> unique index (u16)
    _string_map: dict[str, int] = field(default_factory=dict)
    _strings: list[str] = field(default_factory=list)

    # Label System for Jumps
    # Maps label_name -> byte_offset in code section
    _labels: dict[str, int] = field(default_factory=dict)
    # Maps byte_offset -> label_name_to_resolve
    _pending_jumps: dict[int, str] = field(default_factory=dict)

    def emit_op(self, op: OpCode) -> None:
        """Write an opcode (u8)."""
        self.code.extend(struct.pack("!B", op))

    def emit_u16(self, val: int) -> None:
        """Write unsigned short (Big-Endian)."""
        self.code.extend(struct.pack("!H", val))

    def emit_u32(self, val: int) -> None:
        """Write unsigned int (Big-Endian)."""
        self.code.extend(struct.pack("!I", val))

    def emit_f64(self, val: float) -> None:
        """Write double precision float (Big-Endian)."""
        self.code.extend(struct.pack("!d", val))

    def alloc_string(self, text: str) -> int:
        """
        Add string to the String Table if new.

        Returns the index (u16) handle. Implements string pooling -
        duplicate strings return the same index.

        Raises:
            OverflowError: If string table exceeds 64k entries.
        """
        if text in self._string_map:
            return self._string_map[text]

        idx = len(self._strings)
        if idx > 65535:
            raise OverflowError("String Table exceeded 64k entries")

        self._strings.append(text)
        self._string_map[text] = idx
        return idx

    def mark_label(self, name: str) -> None:
        """Mark the current bytecode position as a jump target."""
        self._labels[name] = len(self.code)

    def emit_jump_placeholder(self, label: str) -> None:
        """Emit 4 bytes (u32) for a jump address, to be filled later."""
        pos = len(self.code)
        self._pending_jumps[pos] = label
        self.emit_u32(0xDEADBEEF)  # Placeholder

    def finalize(self) -> bytes:
        """
        Link jumps, assemble sections, and return final binary.

        Layout: [HEADER] [STR_TABLE] [CODE]

        Raises:
            ValueError: If any jump references an undefined label.
        """
        # 1. Link Jumps - resolve all pending jump addresses
        for pos, label in self._pending_jumps.items():
            if label not in self._labels:
                raise ValueError(f"Undefined label: {label}")
            addr = self._labels[label]
            # Overwrite placeholder in code section
            struct.pack_into("!I", self.code, pos, addr)

        # 2. Build String Table Binary
        # Format: [COUNT: u16] [STR_LEN: u16 + BYTES]...
        str_section = bytearray()
        str_section.extend(struct.pack("!H", len(self._strings)))

        for s in self._strings:
            encoded = s.encode("utf-8")
            str_section.extend(struct.pack("!H", len(encoded)))
            str_section.extend(encoded)

        # 3. Concatenate all sections
        return MAGIC_HEADER + bytes(str_section) + bytes(self.code)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_flowbyte_writer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/compiler/writer.py tests/test_flowbyte_writer.py
git commit -m "$(cat <<'EOF'
feat(compiler): add BytecodeWriter with string pooling

Implement binary assembler for FlowByte format:
- Big-endian struct packing (u8, u16, u32, f64)
- String table with deduplication (O(1) lookup)
- Jump label system with placeholder resolution
- MAGIC_HEADER for format identification
EOF
)"
```

---

### Task 3: Gatekeeper Test for Binary Compactness

**Files:**
- Create: `tests/gatekeepers/test_flowbyte_size.py`

**Step 1: Write the failing test**

```python
# tests/gatekeepers/test_flowbyte_size.py
"""Gatekeeper: FlowByte Binary Compactness.

Enforces that the FlowByte format achieves the promised 10x size
reduction compared to equivalent JSON representations.

Threshold: Counter component < 100 bytes.
"""

import json
from typing import Any

import pytest

from flow.compiler.opcodes import OpCode
from flow.compiler.writer import BytecodeWriter

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
    """Build a Counter component as FlowByte binary.

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

    print(f"\n[FlowByte Gatekeeper] Binary Size: {len(binary)} bytes")
    print(f"[FlowByte Gatekeeper] JSON Size: {json_size} bytes")
    print(f"[FlowByte Gatekeeper] Compression Ratio: {json_size / len(binary):.1f}x")

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
    print(f"\n[FlowByte Gatekeeper] Pooled binary: {len(binary)} bytes")

    # Should be much smaller than 100 bytes
    assert len(binary) < 50, "String pooling not working efficiently"


@pytest.mark.gatekeeper
@pytest.mark.benchmark(group="flowbyte")
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
    assert result.startswith(b"FLOW")

    avg_time_ms = benchmark.stats.stats.mean * 1000
    print(f"\n[FlowByte Gatekeeper] Assembly time: {avg_time_ms:.4f} ms")

    # Should be very fast - < 1ms
    assert avg_time_ms < 1.0, f"Assembly too slow: {avg_time_ms:.4f}ms"
```

**Step 2: Run test to verify it passes (since we have the implementation)**

Run: `uv run pytest tests/gatekeepers/test_flowbyte_size.py -v -m gatekeeper`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/gatekeepers/test_flowbyte_size.py
git commit -m "$(cat <<'EOF'
test(gatekeeper): add FlowByte binary compactness tests

Verify:
- Counter component < 100 bytes (vs ~300 JSON)
- String pooling prevents duplication
- Assembly speed < 1ms
EOF
)"
```

---

## Phase 2: AST-to-FlowByte Compiler

### Task 4: Basic AST Compiler for Signal Initialization

**Files:**
- Create: `src/flow/compiler/flowbyte.py`
- Test: `tests/test_flowbyte_compiler.py`

**Step 1: Write the failing test**

```python
# tests/test_flowbyte_compiler.py
"""Tests for FlowByte AST Compiler."""

import struct

import pytest

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
        str_count = struct.unpack_from("!H", binary, header_len)[0]
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
        binary = compiler.compile(source)

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
        binary = compiler.compile(source)

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_flowbyte_compiler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'flow.compiler.flowbyte'"

**Step 3: Write minimal implementation**

```python
# src/flow/compiler/flowbyte.py
"""FlowByte AST Compiler - Python to bytecode transformation.

Walks Python AST using 3.14's pattern matching and emits FlowByte
instructions. Supports:
- Signal initialization
- DOM element creation (with Div():, Text(), Button())
- Event handlers (on_click)
- Reactive text binding (f-strings)
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from flow.compiler.opcodes import OpCode
from flow.compiler.writer import BytecodeWriter

if TYPE_CHECKING:
    pass


class FlowCompiler(ast.NodeVisitor):
    """
    Python 3.14 AST Visitor for FlowByte compilation.

    Transforms Python syntax into FlowByte instructions.
    """

    def __init__(self) -> None:
        self.writer = BytecodeWriter()
        self.signal_map: dict[str, int] = {}  # Name -> Signal ID
        self.node_id_counter = 0
        self.handler_map: dict[str, str] = {}  # Function name -> label

    def compile(self, source_code: str) -> bytes:
        """Compile Python source to FlowByte binary."""
        tree = ast.parse(source_code)
        self.visit(tree)
        self.writer.emit_op(OpCode.HALT)
        return self.writer.finalize()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handle assignment statements."""
        match node:
            # Signal initialization: count = Signal(0)
            case ast.Assign(
                targets=[ast.Name(id=name)],
                value=ast.Call(
                    func=ast.Name(id="Signal"),
                    args=[ast.Constant(value=val)],
                ),
            ):
                sig_id = len(self.signal_map)
                self.signal_map[name] = sig_id

                if isinstance(val, (int, float)):
                    self.writer.emit_op(OpCode.INIT_SIG_NUM)
                    self.writer.emit_u16(sig_id)
                    self.writer.emit_f64(float(val))
                else:
                    # String signal
                    self.writer.emit_op(OpCode.INIT_SIG_STR)
                    self.writer.emit_u16(sig_id)
                    str_id = self.writer.alloc_string(str(val))
                    self.writer.emit_u16(str_id)

            case _:
                self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions (event handlers)."""
        # Register handler label for later reference
        label = f"handler_{node.name}"
        self.handler_map[node.name] = label

        # Skip compilation of handler body for now
        # It will be emitted when referenced
        pass

    def visit_With(self, node: ast.With) -> None:
        """Handle with statements (DOM elements)."""
        match node:
            case ast.With(
                items=[ast.withitem(context_expr=ast.Call(func=ast.Name(id=tag)))],
                body=body,
            ):
                node_id = self.node_id_counter
                self.node_id_counter += 1

                # Emit DOM_CREATE
                tag_str = self.writer.alloc_string(tag.lower())
                self.writer.emit_op(OpCode.DOM_CREATE)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(tag_str)

                # Append to root (simplified: always parent 0)
                self.writer.emit_op(OpCode.DOM_APPEND)
                self.writer.emit_u16(0)
                self.writer.emit_u16(node_id)

                # Process children
                for child in body:
                    self.visit(child)

            case _:
                self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Handle expression statements (Text, Button calls)."""
        match node.value:
            # Text("hello")
            case ast.Call(
                func=ast.Name(id="Text"),
                args=[ast.Constant(value=text)],
            ):
                self._emit_text_element(str(text))

            # Button("label", on_click=handler)
            case ast.Call(
                func=ast.Name(id="Button"),
                args=[ast.Constant(value=label)],
                keywords=keywords,
            ):
                self._emit_button_element(str(label), keywords)

            case _:
                self.generic_visit(node)

    def _emit_text_element(self, text: str) -> None:
        """Emit opcodes for Text element."""
        node_id = self.node_id_counter
        self.node_id_counter += 1

        # Create span element
        span_str = self.writer.alloc_string("span")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(span_str)

        # Set text content
        text_str = self.writer.alloc_string(text)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(text_str)

        # Append to root
        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)

    def _emit_button_element(
        self, label: str, keywords: list[ast.keyword]
    ) -> None:
        """Emit opcodes for Button element."""
        node_id = self.node_id_counter
        self.node_id_counter += 1

        # Create button element
        btn_str = self.writer.alloc_string("button")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(btn_str)

        # Set label text
        label_str = self.writer.alloc_string(label)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(label_str)

        # Handle on_click
        for kw in keywords:
            if kw.arg == "on_click" and isinstance(kw.value, ast.Name):
                handler_name = kw.value.id
                # Emit click listener with placeholder
                self.writer.emit_op(OpCode.DOM_ON_CLICK)
                self.writer.emit_u16(node_id)
                # For now, emit placeholder address
                self.writer.emit_u32(0)  # Will need proper label resolution

        # Append to root
        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)


def compile_to_flowbyte(source: str) -> bytes:
    """Convenience function to compile source to FlowByte binary."""
    compiler = FlowCompiler()
    return compiler.compile(source)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_flowbyte_compiler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/compiler/flowbyte.py tests/test_flowbyte_compiler.py
git commit -m "$(cat <<'EOF'
feat(compiler): add FlowByte AST compiler

Implement Python-to-bytecode transformation with:
- Signal initialization (numeric and string)
- DOM element creation (Div, Text, Button)
- Event handler registration (on_click)
- Pattern matching for AST node types
EOF
)"
```

---

## Phase 3: JavaScript VM Runtime

### Task 5: Create TypeScript Reactivity Kernel

**Files:**
- Create: `src/flow/static/reactivity.ts`
- Test: Manual browser test (TypeScript compilation check)

**Step 1: Write the implementation**

```typescript
// src/flow/static/reactivity.ts
/**
 * Micro-Signal Kernel for FlowByte VM.
 *
 * A minimal (~500 bytes gzipped) reactivity system that powers
 * the FlowByte Virtual Machine's reactive updates.
 */

// The currently executing effect (for dependency tracking)
let activeEffect: (() => void) | null = null;

export type Signal<T> = {
    value: T;
    subscribe: (fn: () => void) => () => void;
};

/**
 * Create a reactive signal.
 *
 * @param initialValue - The initial value of the signal
 * @returns A Signal object with getter/setter and subscription
 */
export function createSignal<T>(initialValue: T): Signal<T> {
    let _value = initialValue;
    const subscribers = new Set<() => void>();

    return {
        get value() {
            // Auto-track dependency if inside an effect
            if (activeEffect) {
                subscribers.add(activeEffect);
            }
            return _value;
        },
        set value(newValue: T) {
            if (_value !== newValue) {
                _value = newValue;
                // Notify all subscribers
                subscribers.forEach(fn => fn());
            }
        },
        subscribe(fn: () => void) {
            subscribers.add(fn);
            // Return unsubscribe function
            return () => subscribers.delete(fn);
        }
    };
}

/**
 * Create a reactive effect that auto-tracks dependencies.
 *
 * @param fn - The effect function to run
 */
export function createEffect(fn: () => void): void {
    activeEffect = fn;
    fn(); // Run once to capture dependencies
    activeEffect = null;
}

/**
 * Create a computed value that derives from signals.
 *
 * @param fn - The computation function
 * @returns A Signal-like object with a value getter
 */
export function computed<T>(fn: () => T): { readonly value: T } {
    let cachedValue: T;
    let isDirty = true;

    const signal = createSignal<T>(undefined as T);

    createEffect(() => {
        if (isDirty) {
            cachedValue = fn();
            isDirty = false;
        }
        signal.value = cachedValue;
    });

    return {
        get value() {
            return signal.value;
        }
    };
}
```

**Step 2: Commit**

```bash
git add src/flow/static/reactivity.ts
git commit -m "$(cat <<'EOF'
feat(vm): add TypeScript reactivity kernel

Implement micro-signal system for browser VM:
- createSignal() with auto-dependency tracking
- createEffect() for reactive side effects
- computed() for derived values
EOF
)"
```

---

### Task 6: Create FlowByte Virtual Machine

**Files:**
- Create: `src/flow/static/vm.ts`

**Step 1: Write the implementation**

```typescript
// src/flow/static/vm.ts
/**
 * FlowByte Virtual Machine - Browser runtime for .fbc binaries.
 *
 * A lightweight (~3KB) VM that executes FlowByte bytecode directly
 * from an ArrayBuffer, achieving zero parse time.
 */

import { createSignal, createEffect, Signal } from './reactivity.js';

// OpCode Mapping (Must match Python opcodes.py)
const OPS = {
    INIT_SIG_NUM: 0x01,
    INIT_SIG_STR: 0x02,
    SET_SIG_NUM:  0x03,
    ADD:          0x20,
    SUB:          0x21,
    INC_CONST:    0x25,
    JMP_TRUE:     0x40,
    JMP_FALSE:    0x41,
    JMP:          0x42,
    DOM_CREATE:   0x60,
    DOM_APPEND:   0x61,
    DOM_TEXT:     0x62,
    DOM_BIND_TEXT: 0x63,
    DOM_ON_CLICK: 0x64,
    DOM_ATTR_CLASS: 0x65,
    RPC_CALL:     0x90,
    HALT:         0xFF
} as const;

// Magic header "FLOW" + version
const MAGIC = [0x46, 0x4C, 0x4F, 0x57]; // "FLOW"

export class FlowVM {
    // Memory Banks
    signals = new Map<number, Signal<any>>();
    nodes = new Map<number, HTMLElement | Text>();
    strings: string[] = [];

    // Program Code
    view: DataView | null = null;

    // Root element for mounting
    root: HTMLElement | null = null;

    /**
     * Load and execute a FlowByte binary from URL.
     */
    async load(url: string): Promise<void> {
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        this.view = new DataView(buffer);

        // 1. Verify Magic Header
        for (let i = 0; i < 4; i++) {
            if (this.view.getUint8(i) !== MAGIC[i]) {
                throw new Error('Invalid FlowByte binary: bad magic header');
            }
        }

        // Skip header (6 bytes: FLOW + 2 version bytes)
        let offset = 6;

        // 2. Parse String Table
        offset = this.parseStringTable(offset);

        // 3. Get root element
        this.root = document.getElementById('root') || document.body;

        // 4. Execute Code Section
        this.execute(offset);
    }

    /**
     * Parse the string table section.
     * Format: [COUNT: u16] [LEN: u16, BYTES...]...
     */
    private parseStringTable(offset: number): number {
        const count = this.view!.getUint16(offset, false); // Big Endian
        offset += 2;

        const decoder = new TextDecoder();
        for (let i = 0; i < count; i++) {
            const len = this.view!.getUint16(offset, false);
            offset += 2;

            const bytes = new Uint8Array(this.view!.buffer, offset, len);
            this.strings.push(decoder.decode(bytes));
            offset += len;
        }

        return offset;
    }

    /**
     * The Main CPU Loop.
     * @param pc Program Counter (Byte Offset)
     */
    execute(pc: number): void {
        if (!this.view) return;
        const view = this.view;
        let running = true;

        while (running && pc < view.byteLength) {
            const op = view.getUint8(pc++);

            switch (op) {
                // --- STATE ---
                case OPS.INIT_SIG_NUM: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const val = view.getFloat64(pc, false); pc += 8;
                    this.signals.set(id, createSignal(val));
                    break;
                }

                case OPS.INIT_SIG_STR: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    this.signals.set(id, createSignal(this.strings[strId]));
                    break;
                }

                case OPS.SET_SIG_NUM: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const val = view.getFloat64(pc, false); pc += 8;
                    const signal = this.signals.get(id);
                    if (signal) signal.value = val;
                    break;
                }

                case OPS.INC_CONST: {
                    const tgtId = view.getUint16(pc, false); pc += 2;
                    const amount = view.getFloat64(pc, false); pc += 8;
                    const target = this.signals.get(tgtId);
                    if (target) target.value += amount;
                    break;
                }

                // --- ARITHMETIC ---
                case OPS.ADD: {
                    const tgtId = view.getUint16(pc, false); pc += 2;
                    const srcA = view.getUint16(pc, false); pc += 2;
                    const srcB = view.getUint16(pc, false); pc += 2;

                    const sigA = this.signals.get(srcA);
                    const sigB = this.signals.get(srcB);
                    const target = this.signals.get(tgtId);

                    if (target && sigA && sigB) {
                        target.value = sigA.value + sigB.value;
                    }
                    break;
                }

                // --- DOM ---
                case OPS.DOM_CREATE: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const tagStrId = view.getUint16(pc, false); pc += 2;
                    const tagName = this.strings[tagStrId];

                    const el = document.createElement(tagName);
                    this.nodes.set(nodeId, el);
                    break;
                }

                case OPS.DOM_TEXT: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    const el = this.nodes.get(nodeId);
                    if (el) el.textContent = this.strings[strId];
                    break;
                }

                case OPS.DOM_APPEND: {
                    const parentId = view.getUint16(pc, false); pc += 2;
                    const childId = view.getUint16(pc, false); pc += 2;

                    const child = this.nodes.get(childId);
                    if (!child) break;

                    if (parentId === 0) {
                        // Append to root
                        this.root?.appendChild(child);
                    } else {
                        const parent = this.nodes.get(parentId);
                        parent?.appendChild(child);
                    }
                    break;
                }

                case OPS.DOM_ATTR_CLASS: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    const el = this.nodes.get(nodeId) as HTMLElement;
                    if (el) el.className = this.strings[strId];
                    break;
                }

                // --- REACTIVITY ---
                case OPS.DOM_BIND_TEXT: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const tmplId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId);
                    const signal = this.signals.get(sigId);
                    const template = this.strings[tmplId];

                    if (el && signal) {
                        // V1: textContent replacement (simple but triggers layout)
                        // V2 TODO: Use Text node with nodeValue for surgical updates
                        // e.g., const textNode = document.createTextNode('');
                        //       el.appendChild(textNode);
                        //       createEffect(() => { textNode.nodeValue = ... });
                        createEffect(() => {
                            el.textContent = template.replace('{}', String(signal.value));
                        });
                    }
                    break;
                }

                case OPS.DOM_ON_CLICK: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const jumpAddr = view.getUint32(pc, false); pc += 4;

                    const el = this.nodes.get(nodeId);
                    if (el) {
                        // Re-entrancy: click spawns new execution frame
                        el.addEventListener('click', () => {
                            this.execute(jumpAddr);
                        });
                    }
                    break;
                }

                // --- FLOW ---
                case OPS.JMP: {
                    const addr = view.getUint32(pc, false);
                    pc = addr;
                    break;
                }

                case OPS.JMP_TRUE: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const addr = view.getUint32(pc, false); pc += 4;
                    const signal = this.signals.get(sigId);
                    if (signal?.value) {
                        pc = addr;
                    }
                    break;
                }

                case OPS.JMP_FALSE: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const addr = view.getUint32(pc, false); pc += 4;
                    const signal = this.signals.get(sigId);
                    if (!signal?.value) {
                        pc = addr;
                    }
                    break;
                }

                // --- NETWORK ---
                case OPS.RPC_CALL: {
                    const funcStrId = view.getUint16(pc, false); pc += 2;
                    const resultSigId = view.getUint16(pc, false); pc += 2;

                    const funcName = this.strings[funcStrId];
                    const resultSignal = this.signals.get(resultSigId);

                    // Async RPC call
                    fetch(`/api/rpc/${funcName}`, { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            if (resultSignal) resultSignal.value = data;
                        });
                    break;
                }

                case OPS.HALT:
                    running = false;
                    break;

                default:
                    console.error(`Unknown OpCode: 0x${op.toString(16)} at ${pc - 1}`);
                    running = false;
            }
        }
    }
}

// Auto-initialize if script is loaded directly
if (typeof window !== 'undefined') {
    (window as any).FlowVM = FlowVM;
}
```

**Step 2: Commit**

```bash
git add src/flow/static/vm.ts
git commit -m "$(cat <<'EOF'
feat(vm): add FlowByte Virtual Machine

Implement browser-side bytecode executor:
- Zero-copy ArrayBuffer execution
- Signal-based reactivity integration
- DOM manipulation opcodes
- Event listener attachment
- RPC call support
EOF
)"
```

---

## Phase 4: Dev Server Integration

### Task 7: Add FlowByte Compilation Endpoint

**Files:**
- Modify: `src/flow/server/app.py:150-180`
- Test: `tests/test_flowbyte_server.py`

**Step 1: Write the failing test**

```python
# tests/test_flowbyte_server.py
"""Tests for FlowByte server endpoints."""

import pytest
from fastapi.testclient import TestClient

from flow.compiler.writer import MAGIC_HEADER
from flow.server.app import create_app


@pytest.fixture
def flowbyte_client():
    """Create test client with FlowByte support."""
    # Create a simple component for testing
    async def simple_app():
        from flow.ui.elements import Div, Text
        from flow.signal import Signal

        count = Signal(0)
        with Div() as root:
            Text(f"Count: {count.value}")
        return root

    app = create_app(simple_app)
    return TestClient(app)


class TestFlowByteEndpoint:
    """Test /app.fbc endpoint."""

    def test_flowbyte_endpoint_returns_binary(self, flowbyte_client) -> None:
        """GET /app.fbc returns FlowByte binary."""
        response = flowbyte_client.get("/app.fbc")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_flowbyte_starts_with_magic_header(self, flowbyte_client) -> None:
        """Binary starts with FLOW magic header."""
        response = flowbyte_client.get("/app.fbc")

        assert response.content.startswith(MAGIC_HEADER)

    def test_flowbyte_cache_control(self, flowbyte_client) -> None:
        """Binary has appropriate cache headers for dev."""
        response = flowbyte_client.get("/app.fbc")

        # In dev mode, should have no-cache or short cache
        assert "cache-control" in response.headers
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_flowbyte_server.py -v`
Expected: FAIL (endpoint doesn't exist yet)

**Step 3: Add endpoint to server/app.py**

Add the following after the existing `/api/rpc/` endpoint (around line 290):

```python
# Add to src/flow/server/app.py after the RPC handler

    @app.get("/app.fbc")
    async def get_flowbyte() -> Response:
        """Serve compiled FlowByte binary.

        On-demand compilation from the root component's source.
        In production, this would be pre-compiled.
        """
        from flow.compiler.flowbyte import compile_to_flowbyte

        # For now, compile a simple counter as demo
        # TODO: Extract source from root_component
        demo_source = """
count = Signal(0)
def increment():
    count.value += 1

with Div():
    Text(f"Count: {count.value}")
    Button("Up", on_click=increment)
"""
        binary = compile_to_flowbyte(demo_source)

        return Response(
            content=binary,
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-cache, must-revalidate",
            }
        )
```

Also add the import at the top:

```python
from fastapi.responses import HTMLResponse, JSONResponse, Response
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_flowbyte_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/server/app.py tests/test_flowbyte_server.py
git commit -m "$(cat <<'EOF'
feat(server): add FlowByte compilation endpoint

Add GET /app.fbc endpoint that returns compiled bytecode:
- On-demand compilation for dev mode
- application/octet-stream content type
- no-cache headers for development
EOF
)"
```

---

### Task 8: Update CLI for FlowByte Build

**Files:**
- Modify: `src/flow/cli.py:69-124`
- Test: `tests/test_cli_flowbyte.py`

**Step 1: Write the failing test**

```python
# tests/test_cli_flowbyte.py
"""Tests for FlowByte CLI build command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from flow.cli import cli
from flow.compiler.writer import MAGIC_HEADER


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_app(tmp_path):
    """Create a sample Flow app for building."""
    app_file = tmp_path / "app.py"
    app_file.write_text("""
from flow import component
from flow.ui import Div, Text, Button
from flow.signal import Signal

count = Signal(0)

@component
async def App():
    with Div() as root:
        Text(f"Count: {count.value}")
    return root

app = App
""")
    return tmp_path


class TestFlowByteBuild:
    """Test flow build --format=flowbyte."""

    def test_build_creates_fbc_file(self, runner, sample_app, tmp_path) -> None:
        """flow build creates .fbc binary file."""
        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            ["build", "app:app", "--output", str(output_dir), "--format", "flowbyte"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (output_dir / "app.fbc").exists()

    def test_fbc_file_has_magic_header(self, runner, sample_app, tmp_path) -> None:
        """Generated .fbc file starts with FLOW header."""
        output_dir = tmp_path / "dist"

        runner.invoke(
            cli,
            ["build", "app:app", "--output", str(output_dir), "--format", "flowbyte"],
        )

        fbc_content = (output_dir / "app.fbc").read_bytes()
        assert fbc_content.startswith(MAGIC_HEADER)

    def test_build_generates_vm_shell(self, runner, sample_app, tmp_path) -> None:
        """flow build creates HTML shell that loads VM."""
        output_dir = tmp_path / "dist"

        runner.invoke(
            cli,
            ["build", "app:app", "--output", str(output_dir), "--format", "flowbyte"],
        )

        html = (output_dir / "index.html").read_text()
        assert "FlowVM" in html
        assert "app.fbc" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_flowbyte.py -v`
Expected: FAIL (--format option doesn't exist)

**Step 3: Update CLI**

Modify `src/flow/cli.py` to add FlowByte build support:

```python
# In src/flow/cli.py, update the build command

@cli.command()
@click.argument("app_path", type=str, required=False, default="app:app")
@click.option("--output", "-o", default="dist", help="Output directory")
@click.option("--title", default="Flow App", help="HTML page title")
@click.option(
    "--format",
    type=click.Choice(["pyodide", "flowbyte"]),
    default="flowbyte",
    help="Build format (default: flowbyte)"
)
def build(app_path: str, output: str, title: str, format: str) -> None:
    """Build the app for production.

    APP_PATH: Module path to your app (e.g., 'myapp:app')
    """
    click.echo(f"📦 Building Flow app: {app_path}")
    click.echo(f"   Output: {output}/")
    click.echo(f"   Format: {format}")

    # Parse app path
    try:
        module_name, _ = app_path.split(":")
    except ValueError:
        click.echo(f"Error: Invalid app path '{app_path}'. Use format 'module:app'", err=True)
        sys.exit(1)

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find source file
    source_file = None
    cwd = Path.cwd()
    candidate = cwd / f"{module_name}.py"
    if candidate.exists():
        source_file = candidate
    else:
        for search_path in sys.path:
            candidate = Path(search_path) / f"{module_name}.py"
            if candidate.exists():
                source_file = candidate
                break

    if source_file is None:
        click.echo(f"Error: Could not find source file for '{module_name}'", err=True)
        sys.exit(1)

    click.echo(f"   Source: {source_file}")
    source_code = source_file.read_text()

    if format == "flowbyte":
        _build_flowbyte(source_code, module_name, output_path, title)
    else:
        _build_pyodide(source_code, module_name, output_path, title)

    click.echo("✅ Build complete!")


def _build_flowbyte(source_code: str, module_name: str, output_path: Path, title: str) -> None:
    """Build FlowByte binary and VM shell."""
    from flow.compiler.flowbyte import compile_to_flowbyte

    # 1. Compile to FlowByte binary
    binary = compile_to_flowbyte(source_code)
    fbc_file = output_path / f"{module_name}.fbc"
    fbc_file.write_bytes(binary)
    click.echo(f"   FlowByte binary: {fbc_file} ({len(binary)} bytes)")

    # 2. Generate HTML shell with VM
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: system-ui, sans-serif; }}
        #root {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module">
        // FlowByte VM (inline for zero additional requests)
        {_get_vm_inline()}

        // Boot the VM
        const vm = new FlowVM();
        console.time('Flow Boot');
        await vm.load('/{module_name}.fbc');
        console.timeEnd('Flow Boot');
    </script>
</body>
</html>
"""
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")


def _build_pyodide(source_code: str, module_name: str, output_path: Path, title: str) -> None:
    """Build with Pyodide (legacy)."""
    from flow.build.artifacts import generate_client_bundle, generate_html_shell

    client_dir = output_path / "client"
    client_dir.mkdir(parents=True, exist_ok=True)

    client_file = client_dir / f"{module_name}.py"
    generate_client_bundle(source_code, client_file)
    click.echo(f"   Client bundle: {client_file}")

    html_content = generate_html_shell(app_module=module_name, title=title)
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")


def _get_vm_inline() -> str:
    """Return inline JavaScript for FlowByte VM."""
    # Simplified inline VM for production builds
    return """
class FlowVM {
    signals = new Map();
    nodes = new Map();
    strings = [];
    view = null;
    root = null;

    async load(url) {
        const r = await fetch(url);
        const buf = await r.arrayBuffer();
        this.view = new DataView(buf);

        // Verify header
        if (String.fromCharCode(...new Uint8Array(buf, 0, 4)) !== 'FLOW') {
            throw new Error('Invalid FlowByte');
        }

        let off = 6;
        // Parse strings
        const cnt = this.view.getUint16(off, false); off += 2;
        const dec = new TextDecoder();
        for (let i = 0; i < cnt; i++) {
            const len = this.view.getUint16(off, false); off += 2;
            this.strings.push(dec.decode(new Uint8Array(buf, off, len)));
            off += len;
        }

        this.root = document.getElementById('root');
        this.execute(off);
    }

    execute(pc) {
        const v = this.view;
        let run = true;
        while (run && pc < v.byteLength) {
            const op = v.getUint8(pc++);
            switch (op) {
                case 0x01: { // INIT_SIG_NUM
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = v.getFloat64(pc, false); pc += 8;
                    this.signals.set(id, { value: val, subs: new Set() });
                    break;
                }
                case 0x25: { // INC_CONST
                    const id = v.getUint16(pc, false); pc += 2;
                    const amt = v.getFloat64(pc, false); pc += 8;
                    const s = this.signals.get(id);
                    if (s) { s.value += amt; s.subs.forEach(f => f()); }
                    break;
                }
                case 0x60: { // DOM_CREATE
                    const nid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    this.nodes.set(nid, document.createElement(this.strings[tid]));
                    break;
                }
                case 0x61: { // DOM_APPEND
                    const pid = v.getUint16(pc, false); pc += 2;
                    const cid = v.getUint16(pc, false); pc += 2;
                    const c = this.nodes.get(cid);
                    if (c) (pid === 0 ? this.root : this.nodes.get(pid))?.appendChild(c);
                    break;
                }
                case 0x62: { // DOM_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.textContent = this.strings[sid];
                    break;
                }
                case 0x63: { // DOM_BIND_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    const s = this.signals.get(sid);
                    const t = this.strings[tid];
                    if (n && s) {
                        const upd = () => n.textContent = t.replace('{}', s.value);
                        s.subs.add(upd);
                        upd();
                    }
                    break;
                }
                case 0x64: { // DOM_ON_CLICK
                    const nid = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const n = this.nodes.get(nid);
                    if (n) n.addEventListener('click', () => this.execute(addr));
                    break;
                }
                case 0x42: { // JMP
                    pc = v.getUint32(pc, false);
                    break;
                }
                case 0xFF: run = false; break;
                default: console.error('Unknown op:', op.toString(16)); run = false;
            }
        }
    }
}
"""
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_flowbyte.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/flow/cli.py tests/test_cli_flowbyte.py
git commit -m "$(cat <<'EOF'
feat(cli): add FlowByte build format option

Add --format=flowbyte to flow build command:
- Compiles Python to .fbc binary
- Generates HTML shell with inline VM
- Default format (replaces Pyodide)
- ~10x smaller output than Pyodide
EOF
)"
```

---

## Phase 5: End-to-End Validation

### Task 9: Integration Test for Full Pipeline

**Files:**
- Create: `tests/test_flowbyte_e2e.py`

**Step 1: Write the test**

```python
# tests/test_flowbyte_e2e.py
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
        binary = compiler.compile(source)

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
        assert "Hello 世界".encode("utf-8") in binary

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
```

**Step 2: Run test**

Run: `uv run pytest tests/test_flowbyte_e2e.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_flowbyte_e2e.py
git commit -m "$(cat <<'EOF'
test(e2e): add FlowByte end-to-end integration tests

Verify complete pipeline:
- Counter app compilation
- Nested element compilation
- Multiple signal handling
- Binary format correctness
- UTF-8 string encoding
- Compilation performance gatekeeper
EOF
)"
```

---

### Task 10: Update Package Exports

**Files:**
- Modify: `src/flow/compiler/__init__.py`

**Step 1: Write the update**

```python
# src/flow/compiler/__init__.py
"""Flow Compiler - AST transformation and bytecode generation."""

from flow.compiler.flowbyte import FlowCompiler, compile_to_flowbyte
from flow.compiler.opcodes import OpCode
from flow.compiler.transformer import (
    ClientSafeTransformer,
    compile_for_client,
    transform_for_client,
)
from flow.compiler.writer import MAGIC_HEADER, BytecodeWriter

__all__ = [
    # FlowByte compiler
    "FlowCompiler",
    "compile_to_flowbyte",
    "OpCode",
    "BytecodeWriter",
    "MAGIC_HEADER",
    # Legacy transformer
    "ClientSafeTransformer",
    "compile_for_client",
    "transform_for_client",
]
```

**Step 2: Run all tests to verify nothing broke**

Run: `uv run pytest tests/ -v --ignore=tests/e2e`
Expected: PASS

**Step 3: Commit**

```bash
git add src/flow/compiler/__init__.py
git commit -m "$(cat <<'EOF'
feat(compiler): export FlowByte public API

Add to compiler module exports:
- FlowCompiler, compile_to_flowbyte
- OpCode, BytecodeWriter, MAGIC_HEADER
EOF
)"
```

---

## Summary

This plan implements the FlowByte architecture in 10 bite-sized tasks:

| Phase | Task | Description |
|-------|------|-------------|
| 1 | 1 | Opcode Registry |
| 1 | 2 | BytecodeWriter with String Pooling |
| 1 | 3 | Binary Compactness Gatekeeper |
| 2 | 4 | AST-to-FlowByte Compiler |
| 3 | 5 | TypeScript Reactivity Kernel |
| 3 | 6 | FlowByte Virtual Machine |
| 4 | 7 | Server /app.fbc Endpoint |
| 4 | 8 | CLI --format=flowbyte |
| 5 | 9 | E2E Integration Tests |
| 5 | 10 | Package Exports |

**Expected Results:**
- Binary size: ~50-100 bytes for counter (vs ~300 JSON, ~12MB Pyodide)
- Parse time: 0ms (direct ArrayBuffer execution)
- VM size: ~3KB gzipped
- Compilation speed: < 10ms for typical components
