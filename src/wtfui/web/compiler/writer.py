import struct
from dataclasses import dataclass, field

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.sourcemap import FileIndex, LineNumber, ProgramCounter, SourceMap

MAGIC_HEADER = b"MYFU\x00\x01"


@dataclass
class BytecodeWriter:
    code: bytearray = field(default_factory=bytearray)

    _string_map: dict[str, int] = field(default_factory=dict)
    _strings: list[str] = field(default_factory=list)

    _labels: dict[str, int] = field(default_factory=dict)

    _pending_jumps: dict[int, str] = field(default_factory=dict)

    source_map: SourceMap = field(default_factory=SourceMap)
    _current_file_idx: FileIndex = field(default_factory=lambda: FileIndex(0))

    def emit_op(self, op: OpCode) -> None:
        self.code.extend(struct.pack("!B", op))

    def emit_u8(self, val: int) -> None:
        self.code.extend(struct.pack("!B", val))

    def emit_u16(self, val: int) -> None:
        self.code.extend(struct.pack("!H", val))

    def emit_u32(self, val: int) -> None:
        self.code.extend(struct.pack("!I", val))

    def emit_f64(self, val: float) -> None:
        self.code.extend(struct.pack("!d", val))

    def alloc_string(self, text: str) -> int:
        if text in self._string_map:
            return self._string_map[text]

        idx = len(self._strings)
        if idx >= 65535:
            raise OverflowError("String Table exceeded 64k entries")

        self._strings.append(text)
        self._string_map[text] = idx
        return idx

    def mark_label(self, name: str) -> None:
        self._labels[name] = len(self.code)

    def emit_jump_placeholder(self, label: str) -> None:
        pos = len(self.code)
        self._pending_jumps[pos] = label
        self.emit_u32(0xDEADBEEF)

    def finalize(self) -> bytes:
        for pos, label in self._pending_jumps.items():
            if label not in self._labels:
                raise ValueError(f"Undefined label: {label}")
            addr = self._labels[label]

            struct.pack_into("!I", self.code, pos, addr)

        str_section = bytearray()
        str_section.extend(struct.pack("!H", len(self._strings)))

        for s in self._strings:
            encoded = s.encode("utf-8")
            str_section.extend(struct.pack("!H", len(encoded)))
            str_section.extend(encoded)

        return MAGIC_HEADER + bytes(str_section) + bytes(self.code)

    def set_file(self, filename: str) -> None:
        self._current_file_idx = self.source_map.add_file(filename)

    def mark_location(self, lineno: int) -> None:
        pc = ProgramCounter(len(self.code))
        self.source_map.add_mapping(pc, self._current_file_idx, LineNumber(lineno))

    def finalize_map(self) -> bytes:
        return self.source_map.to_bytes()
