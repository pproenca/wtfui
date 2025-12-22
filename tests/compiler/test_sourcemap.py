"""Tests for WtfUIByte Source Map (.fsm) generation and parsing."""

import pytest

from wtfui.web.compiler.sourcemap import FSM_MAGIC, SourceMap


class TestSourceMapDataStructure:
    """Test SourceMap basic operations."""

    def test_add_file_returns_index(self) -> None:
        """Adding a file returns its index."""
        sm = SourceMap()
        idx = sm.add_file("app.py")
        assert idx == 0

    def test_add_file_deduplicates(self) -> None:
        """Adding same file twice returns same index."""
        sm = SourceMap()
        idx1 = sm.add_file("app.py")
        idx2 = sm.add_file("app.py")
        assert idx1 == idx2 == 0

    def test_add_mapping_records_entry(self) -> None:
        """Adding a mapping records PC, file, and line."""
        sm = SourceMap()
        file_idx = sm.add_file("app.py")
        sm.add_mapping(pc=0, file_idx=file_idx, line=1)
        assert len(sm.mappings) == 1
        assert sm.mappings[0] == (0, 0, 1)

    def test_add_mapping_deduplicates_same_location(self) -> None:
        """Consecutive mappings to same location are deduplicated."""
        sm = SourceMap()
        file_idx = sm.add_file("app.py")
        sm.add_mapping(pc=0, file_idx=file_idx, line=1)
        sm.add_mapping(pc=5, file_idx=file_idx, line=1)  # Same line
        assert len(sm.mappings) == 1  # Still just one entry


class TestSourceMapBinarySerialization:
    """Test .fsm binary format serialization."""

    def test_to_bytes_has_magic_header(self) -> None:
        """Serialized map starts with FSM_MAGIC."""
        sm = SourceMap()
        data = sm.to_bytes()
        assert data.startswith(FSM_MAGIC)

    def test_roundtrip_empty_map(self) -> None:
        """Empty map survives serialization roundtrip."""
        sm = SourceMap()
        data = sm.to_bytes()
        restored = SourceMap.from_bytes(data)
        assert restored.files == []
        assert restored.mappings == []

    def test_roundtrip_with_files_and_mappings(self) -> None:
        """Map with data survives serialization roundtrip."""
        sm = SourceMap()
        f1 = sm.add_file("app.py")
        f2 = sm.add_file("utils.py")
        sm.add_mapping(pc=0, file_idx=f1, line=1)
        sm.add_mapping(pc=10, file_idx=f1, line=5)
        sm.add_mapping(pc=50, file_idx=f2, line=12)

        data = sm.to_bytes()
        restored = SourceMap.from_bytes(data)

        assert restored.files == ["app.py", "utils.py"]
        assert restored.mappings == [(0, 0, 1), (10, 0, 5), (50, 1, 12)]

    def test_from_bytes_rejects_invalid_magic(self) -> None:
        """Invalid magic header raises ValueError."""
        with pytest.raises(ValueError, match="Invalid FSM magic"):
            SourceMap.from_bytes(b"BAAD\x00\x01")


class TestSourceMapLookup:
    """Test PC to source location lookup."""

    def test_lookup_exact_match(self) -> None:
        """lookup_pc finds exact PC match."""
        sm = SourceMap()
        f = sm.add_file("app.py")
        sm.add_mapping(pc=0, file_idx=f, line=1)
        sm.add_mapping(pc=10, file_idx=f, line=5)

        result = sm.lookup_pc(10)
        assert result is not None
        file, line = result
        assert file == "app.py"
        assert line == 5

    def test_lookup_between_mappings(self) -> None:
        """lookup_pc finds nearest preceding mapping."""
        sm = SourceMap()
        f = sm.add_file("app.py")
        sm.add_mapping(pc=0, file_idx=f, line=1)
        sm.add_mapping(pc=20, file_idx=f, line=10)

        result = sm.lookup_pc(15)  # Between 0 and 20
        assert result is not None
        file, line = result
        assert file == "app.py"
        assert line == 1  # Maps to line 1 (PC 0)

    def test_lookup_not_found_returns_none(self) -> None:
        """lookup_pc returns None for unmapped PC."""
        sm = SourceMap()
        result = sm.lookup_pc(100)
        assert result is None


class TestBytecodeWriterSourceMapIntegration:
    """Test BytecodeWriter source map tracking."""

    def test_set_file_registers_in_source_map(self) -> None:
        """set_file adds file to source map."""
        from wtfui.web.compiler.writer import BytecodeWriter

        writer = BytecodeWriter()
        writer.set_file("app.py")
        assert "app.py" in writer.source_map.files

    def test_mark_location_records_mapping(self) -> None:
        """mark_location records PC before next opcode."""
        from wtfui.web.compiler.opcodes import OpCode
        from wtfui.web.compiler.writer import BytecodeWriter

        writer = BytecodeWriter()
        writer.set_file("app.py")
        writer.mark_location(lineno=5)
        writer.emit_op(OpCode.HALT)

        assert len(writer.source_map.mappings) == 1
        pc, _file_idx, line = writer.source_map.mappings[0]
        assert pc == 0  # Before HALT
        assert line == 5

    def test_mark_location_tracks_multiple_lines(self) -> None:
        """mark_location tracks opcodes from different lines."""
        from wtfui.web.compiler.opcodes import OpCode
        from wtfui.web.compiler.writer import BytecodeWriter

        writer = BytecodeWriter()
        writer.set_file("app.py")

        writer.mark_location(lineno=1)
        writer.emit_op(OpCode.PUSH_NUM)
        writer.emit_f64(42.0)

        writer.mark_location(lineno=2)
        writer.emit_op(OpCode.POP)
        writer.emit_u8(1)

        assert len(writer.source_map.mappings) == 2
        # First mapping at PC 0 (PUSH_NUM)
        assert writer.source_map.mappings[0] == (0, 0, 1)
        # Second mapping at PC 9 (PUSH_NUM is 1 byte, f64 is 8 bytes)
        assert writer.source_map.mappings[1] == (9, 0, 2)

    def test_finalize_map_returns_fsm_bytes(self) -> None:
        """finalize_map returns valid .fsm binary."""
        from wtfui.web.compiler.opcodes import OpCode
        from wtfui.web.compiler.writer import BytecodeWriter

        writer = BytecodeWriter()
        writer.set_file("app.py")
        writer.mark_location(lineno=1)
        writer.emit_op(OpCode.HALT)

        fsm_bytes = writer.finalize_map()
        assert fsm_bytes.startswith(b"FSM")

        # Verify roundtrip
        sm = SourceMap.from_bytes(fsm_bytes)
        assert sm.files == ["app.py"]
        assert sm.mappings[0][2] == 1  # Line 1


class TestWtfUICompilerSourceMapGeneration:
    """Test WtfUICompiler generates source maps."""

    def test_compile_full_returns_sourcemap(self) -> None:
        """compile_full returns (bytecode, css, sourcemap) tuple."""
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        compiler = WtfUICompiler()
        source = "count = Signal(0)"
        fbc, css, fsm = compiler.compile_full(source, filename="app.py")

        assert isinstance(fbc, bytes)
        assert isinstance(css, str)
        assert isinstance(fsm, bytes)
        assert fsm.startswith(b"FSM")

    def test_sourcemap_contains_correct_file(self) -> None:
        """Source map contains the compiled filename."""
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        compiler = WtfUICompiler()
        source = "count = Signal(0)"
        _, _, fsm = compiler.compile_full(source, filename="myapp.py")

        sm = SourceMap.from_bytes(fsm)
        assert "myapp.py" in sm.files

    def test_sourcemap_maps_signal_to_line(self) -> None:
        """Source map correctly maps signal init to its line."""
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        compiler = WtfUICompiler()
        source = """
count = Signal(0)
"""
        _, _, fsm = compiler.compile_full(source, filename="app.py")

        sm = SourceMap.from_bytes(fsm)
        # Signal init should map to line 2 (blank line 1)
        lines = [m[2] for m in sm.mappings]
        assert 2 in lines

    def test_sourcemap_maps_multiple_statements(self) -> None:
        """Source map tracks multiple statements on different lines."""
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        compiler = WtfUICompiler()
        source = """count = Signal(0)
other = Signal(1)
"""
        _, _, fsm = compiler.compile_full(source, filename="app.py")

        sm = SourceMap.from_bytes(fsm)
        lines = sorted({m[2] for m in sm.mappings})
        # Should have mappings for lines 1 and 2
        assert 1 in lines
        assert 2 in lines
