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

from flow.compiler.opcodes import OpCode  # noqa: TC001

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
        if idx >= 65535:
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
