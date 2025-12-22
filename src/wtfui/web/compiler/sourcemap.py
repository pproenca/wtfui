import struct
from dataclasses import dataclass, field
from typing import NewType

ProgramCounter = NewType("ProgramCounter", int)
FileIndex = NewType("FileIndex", int)
LineNumber = NewType("LineNumber", int)


FSM_MAGIC = b"FSM\x00\x01"


@dataclass
class SourceMap:
    files: list[str] = field(default_factory=list)

    mappings: list[tuple[ProgramCounter, FileIndex, LineNumber]] = field(default_factory=list)

    def add_file(self, filename: str) -> FileIndex:
        if filename in self.files:
            return FileIndex(self.files.index(filename))
        self.files.append(filename)
        return FileIndex(len(self.files) - 1)

    def add_mapping(self, pc: ProgramCounter, file_idx: FileIndex, line: LineNumber) -> None:
        if self.mappings and self.mappings[-1][1:] == (file_idx, line):
            return
        self.mappings.append((pc, file_idx, line))

    def lookup_pc(self, pc: ProgramCounter) -> tuple[str, LineNumber] | None:
        if not self.mappings:
            return None

        left, right = 0, len(self.mappings) - 1
        result_idx = -1

        while left <= right:
            mid = (left + right) // 2
            if self.mappings[mid][0] <= pc:
                result_idx = mid
                left = mid + 1
            else:
                right = mid - 1

        if result_idx < 0:
            return None

        _, file_idx, line = self.mappings[result_idx]
        return (self.files[file_idx], line)

    def to_bytes(self) -> bytes:
        buf = bytearray(FSM_MAGIC)

        buf.extend(struct.pack("!H", len(self.files)))
        for f in self.files:
            encoded = f.encode("utf-8")
            buf.extend(struct.pack("!H", len(encoded)))
            buf.extend(encoded)

        buf.extend(struct.pack("!I", len(self.mappings)))
        for pc, file_idx, line in self.mappings:
            buf.extend(struct.pack("!IHI", pc, file_idx, line))

        return bytes(buf)

    @classmethod
    def from_bytes(cls, data: bytes) -> SourceMap:
        if not data.startswith(FSM_MAGIC):
            raise ValueError("Invalid FSM magic header")

        sm = cls()
        offset = len(FSM_MAGIC)

        (file_count,) = struct.unpack_from("!H", data, offset)
        offset += 2
        for _ in range(file_count):
            (length,) = struct.unpack_from("!H", data, offset)
            offset += 2
            sm.files.append(data[offset : offset + length].decode("utf-8"))
            offset += length

        (map_count,) = struct.unpack_from("!I", data, offset)
        offset += 4
        for _ in range(map_count):
            pc, file_idx, line = struct.unpack_from("!IHI", data, offset)
            sm.mappings.append(
                (
                    ProgramCounter(pc),
                    FileIndex(file_idx),
                    LineNumber(line),
                )
            )
            offset += 10

        return sm
