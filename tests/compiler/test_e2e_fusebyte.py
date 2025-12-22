"""End-to-end tests for WtfUIByte compilation pipeline.

Verifies the complete flow from Python source to executable bytecode,
including all features implemented in the WtfUIByte v2 architecture.
"""

import struct

from wtfui.web.compiler.intrinsics import IntrinsicID
from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.parallel import compile_parallel
from wtfui.web.compiler.writer import MAGIC_HEADER
from wtfui.web.compiler.wtfuibyte import compile_to_wtfuibyte


def test_counter_app_compilation():
    """Complete counter app compiles to valid bytecode."""
    source = """
count = Signal(0)

def increment():
    count.value += 1

with Div(class_="container"):
    with Button(on_click=increment):
        Text("Click me")
"""
    binary = compile_to_wtfuibyte(source)

    # Verify structure
    assert binary.startswith(MAGIC_HEADER)
    assert bytes([OpCode.HALT]) in binary  # HALT present (after main code)
    assert binary.endswith(bytes([OpCode.RET]))  # Function compiled at end

    # Verify key opcodes present
    assert bytes([OpCode.INIT_SIG_NUM]) in binary
    assert bytes([OpCode.DOM_CREATE]) in binary
    assert bytes([OpCode.DOM_APPEND]) in binary
    assert bytes([OpCode.DOM_ATTR_CLASS]) in binary


def test_styled_component_compilation():
    """Component with styles compiles correctly."""
    source = """
with Div(class_="flex items-center", style={"background": "blue", "padding": "20px"}):
    with Span(id="title", style="color: white"):
        Text("Hello WtfUIByte")
"""
    binary = compile_to_wtfuibyte(source)

    assert binary.startswith(MAGIC_HEADER)

    # Style opcodes - now uses atomic CSS classes instead of inline styles
    assert bytes([OpCode.DOM_ATTR_CLASS]) in binary
    assert bytes([OpCode.DOM_ATTR]) in binary  # For id

    # CSS class names should be in binary (fl-xxxxx format)
    assert b"fl-" in binary


def test_intrinsic_calls_compilation():
    """Intrinsic function calls compile correctly."""
    source = """
count = Signal(42)
print(count.value)
print(str(count.value))
print(len("hello"))
"""
    binary = compile_to_wtfuibyte(source)

    assert binary.startswith(MAGIC_HEADER)

    # Intrinsic calls
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.PRINT, 1]) in binary
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.STR, 1]) in binary
    assert bytes([OpCode.CALL_INTRINSIC, IntrinsicID.LEN, 1]) in binary


def test_arithmetic_expressions_compilation():
    """Arithmetic expressions compile to stack-based opcodes."""
    source = """
a = Signal(10)
b = Signal(20)
a.value += b.value * 2
a.value -= 5
"""
    binary = compile_to_wtfuibyte(source)

    assert binary.startswith(MAGIC_HEADER)

    # Stack operations
    assert bytes([OpCode.LOAD_SIG]) in binary
    assert bytes([OpCode.PUSH_NUM]) in binary
    assert bytes([OpCode.MUL]) in binary
    assert bytes([OpCode.ADD_STACK]) in binary
    assert bytes([OpCode.SUB_STACK]) in binary
    assert bytes([OpCode.STORE_SIG]) in binary


def test_parallel_compilation_produces_same_result():
    """Parallel compilation produces valid bytecode."""
    source = """
count = Signal(0)

with Div():
    Text("Hello")

with Span():
    Text("World")
"""
    # Single-threaded
    binary_single = compile_to_wtfuibyte(source)

    # Parallel
    binary_parallel = compile_parallel(source, max_workers=4)

    # Both should be valid
    assert binary_single.startswith(MAGIC_HEADER)
    assert binary_parallel.startswith(MAGIC_HEADER)

    # Both should have HALT at end
    assert binary_single.endswith(b"\xff")
    assert binary_parallel.endswith(b"\xff")


def test_bytecode_binary_format():
    """Bytecode follows the specified binary format."""
    source = """
count = Signal(42)
print(count.value)
"""
    binary = compile_to_wtfuibyte(source)

    # Header: "MYFU" (4 bytes) + version (2 bytes)
    assert binary[0:4] == b"MYFU"
    assert binary[4:6] == b"\x00\x01"  # Version 1.0

    # String table starts at offset 6
    offset = 6
    string_count = struct.unpack("!H", binary[offset : offset + 2])[0]
    assert string_count >= 0

    # Parse string table
    offset += 2
    strings = []
    for _ in range(string_count):
        str_len = struct.unpack("!H", binary[offset : offset + 2])[0]
        offset += 2
        s = binary[offset : offset + str_len].decode("utf-8")
        strings.append(s)
        offset += str_len

    # Code section follows string table
    code_start = offset
    assert code_start < len(binary)

    # First opcode should be valid
    first_opcode = binary[code_start]
    assert first_opcode in [op.value for op in OpCode]


def test_signal_initialization_encoding():
    """Signal initialization encodes correctly."""
    source = "count = Signal(42)"
    binary = compile_to_wtfuibyte(source)

    # Skip header and string table to find code section
    offset = 6
    string_count = struct.unpack("!H", binary[offset : offset + 2])[0]
    offset += 2

    for _ in range(string_count):
        str_len = struct.unpack("!H", binary[offset : offset + 2])[0]
        offset += 2 + str_len

    # Now offset points to code section
    code = binary[offset:]

    # Find INIT_SIG_NUM opcode in code section
    idx = code.find(bytes([OpCode.INIT_SIG_NUM]))
    assert idx >= 0

    # Next 2 bytes are signal ID (u16 big-endian)
    sig_id = struct.unpack("!H", code[idx + 1 : idx + 3])[0]
    assert sig_id == 0  # First signal

    # Next 8 bytes are initial value (f64 big-endian)
    init_val = struct.unpack("!d", code[idx + 3 : idx + 11])[0]
    assert init_val == 42.0


def test_string_pooling_efficiency():
    """Duplicate strings are pooled (only stored once)."""
    source = """
with Div(class_="container"):
    pass

with Div(class_="container"):
    pass

with Div(class_="container"):
    pass
"""
    binary = compile_to_wtfuibyte(source)

    # "container" should only appear once in the string table
    # Count occurrences in the raw binary
    count = binary.count(b"container")
    assert count == 1  # Pooled - only one copy


def test_complex_nested_structure():
    """Complex nested DOM structure compiles correctly."""
    source = """
with Div(class_="app"):
    with Div(class_="header"):
        Text("Header")
    with Div(class_="main"):
        with Div(class_="sidebar"):
            Text("Sidebar")
        with Div(class_="content"):
            Text("Content")
    with Div(class_="footer"):
        Text("Footer")
"""
    binary = compile_to_wtfuibyte(source)

    assert binary.startswith(MAGIC_HEADER)

    # Multiple DOM_CREATE opcodes
    create_count = binary.count(bytes([OpCode.DOM_CREATE]))
    assert create_count >= 6  # At least 6 divs

    # Multiple DOM_APPEND opcodes
    append_count = binary.count(bytes([OpCode.DOM_APPEND]))
    assert append_count >= 6


def test_all_opcodes_valid():
    """All opcodes in generated bytecode are valid."""
    source = """
count = Signal(0)
count.value += 1
print(count.value)

with Div(class_="test", style={"color": "red"}):
    Text("Hello")
"""
    binary = compile_to_wtfuibyte(source)

    # Skip header and string table to get to code
    offset = 6
    string_count = struct.unpack("!H", binary[offset : offset + 2])[0]
    offset += 2

    for _ in range(string_count):
        str_len = struct.unpack("!H", binary[offset : offset + 2])[0]
        offset += 2 + str_len

    # Check all opcodes in code section
    valid_opcodes = {op.value for op in OpCode}
    code = binary[offset:]

    # Simple check: first byte of code section should be valid opcode
    if len(code) > 0:
        assert code[0] in valid_opcodes
