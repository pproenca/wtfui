# tests/compiler/test_wtfuibyte_functions.py
"""Tests for user-defined function compilation in WtfUIByte."""

import ast

import pytest

from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.wtfuibyte import WtfUICompiler, compile_to_wtfuibyte


def test_function_def_stores_ast_and_label():
    """visit_FunctionDef stores AST node and registers label."""
    source = """
def my_func():
    count.value += 1
"""
    compiler = WtfUICompiler()
    tree = ast.parse(source)
    compiler.visit(tree)

    # function_registry should contain the AST node
    assert "my_func" in compiler.function_registry
    stored = compiler.function_registry["my_func"]
    assert isinstance(stored, ast.FunctionDef)
    assert stored.name == "my_func"


def test_function_with_parameters_raises_error():
    """Functions with parameters raise NotImplementedError."""
    source = """
def add(a, b):
    return a + b
"""
    with pytest.raises(NotImplementedError, match=r"parameters.*not supported"):
        compile_to_wtfuibyte(source)


def test_nested_function_raises_error():
    """Nested functions raise NotImplementedError."""
    source = """
def outer():
    def inner():
        pass
    inner()
"""
    with pytest.raises(NotImplementedError, match=r"[Nn]ested.*not supported"):
        compile_to_wtfuibyte(source)


def test_function_body_compiled_at_end():
    """Function body should be compiled after main code, with RET at end."""
    source = """
count = Signal(0)

def increment():
    count.value += 1
"""
    binary = compile_to_wtfuibyte(source)

    # RET opcode should be present (function was compiled)
    assert bytes([OpCode.RET]) in binary

    # Function should end with RET (last opcode before any trailing bytes)
    ret_pos = binary.rfind(bytes([OpCode.RET]))
    assert ret_pos != -1, "RET not found"

    # RET should be the last significant opcode (function is at end)
    # Note: HALT is emitted before functions, so RET is now at the very end
    assert binary.endswith(bytes([OpCode.RET])), (
        "Expected RET at end of bytecode (functions are compiled after HALT)"
    )


def test_function_call_emits_call_opcode():
    """Calling a user function emits CALL opcode with function address."""
    source = """
count = Signal(0)

def increment():
    count.value += 1

increment()
"""
    binary = compile_to_wtfuibyte(source)

    # CALL opcode should be present
    assert bytes([OpCode.CALL]) in binary

    # RET should also be present (from function body)
    assert bytes([OpCode.RET]) in binary


def test_on_click_handler_uses_function_label():
    """DOM_ON_CLICK uses the function's compiled address, not placeholder."""
    import struct

    source = """
count = Signal(0)

def increment():
    count.value += 1

with Button("Click", on_click=increment):
    pass
"""
    binary = compile_to_wtfuibyte(source)

    # Find DOM_ON_CLICK opcode position
    on_click_pos = binary.find(bytes([OpCode.DOM_ON_CLICK]))
    assert on_click_pos != -1, "DOM_ON_CLICK not found"

    # The address should NOT be 0x00000000 (placeholder)
    # Skip opcode (1 byte) + node_id (2 bytes) to get address (4 bytes)
    addr_start = on_click_pos + 1 + 2
    addr_bytes = binary[addr_start : addr_start + 4]
    addr = struct.unpack("!I", addr_bytes)[0]

    # Should point to a valid address (not 0 placeholder)
    assert addr != 0, "DOM_ON_CLICK still using placeholder address 0"


def test_on_click_with_undefined_handler_warns():
    """on_click with undefined function should warn, not crash."""
    import warnings as warnings_module

    source = """
with Button("Click", on_click=undefined_func):
    pass
"""
    # Should not raise, but emit warning
    with warnings_module.catch_warnings(record=True) as w:
        warnings_module.simplefilter("always")
        binary = compile_to_wtfuibyte(source)

        # Verify compilation succeeded
        assert binary.startswith(b"MYFU")

        # Verify we got a warning about undefined handler
        assert len(w) == 1
        assert "undefined_func" in str(w[0].message)
        assert "not in local function_registry" in str(w[0].message)


def test_recursive_function_compiles():
    """Recursive function compiles without infinite loop."""
    source = """
def countdown():
    if n.value > 0:
        n.value -= 1
        countdown()

n = Signal(5)
countdown()
"""
    # This should complete without hanging
    binary = compile_to_wtfuibyte(source)

    # Should have CALL (for recursive call inside function)
    assert bytes([OpCode.CALL]) in binary

    # Should have RET
    assert bytes([OpCode.RET]) in binary


def test_multiple_calls_use_same_function():
    """Multiple calls to same function use CALL to same address."""
    source = """
count = Signal(0)

def increment():
    count.value += 1

increment()
increment()
increment()
"""
    binary = compile_to_wtfuibyte(source)

    # Should have exactly 3 CALL opcodes
    call_count = binary.count(bytes([OpCode.CALL]))
    assert call_count == 3

    # But only 1 RET (function compiled once)
    ret_count = binary.count(bytes([OpCode.RET]))
    assert ret_count == 1


def test_counter_app_with_handler_and_call():
    """Counter app with both handler reference and explicit call."""
    source = """
count = Signal(0)

def increment():
    count.value += 1

with Div(class_="container"):
    with Button("Click", on_click=increment):
        pass
    increment()  # Explicit call too
"""
    binary = compile_to_wtfuibyte(source)

    # Verify structure
    assert binary.startswith(b"MYFU")
    assert bytes([OpCode.HALT]) in binary  # HALT present (after main code)
    assert binary.endswith(bytes([OpCode.RET]))  # Function compiled at end

    # Should have DOM_ON_CLICK pointing to function
    assert bytes([OpCode.DOM_ON_CLICK]) in binary

    # Should have CALL for explicit call
    assert bytes([OpCode.CALL]) in binary

    # Only one RET (function compiled once)
    assert binary.count(bytes([OpCode.RET])) == 1


def test_main_code_halts_before_functions():
    """Main code must HALT before function definitions to prevent fallthrough.

    Bug: Without HALT after main code, the VM would execute function bodies
    as if they were inline code, causing unintended side effects.
    """
    source = """
count = Signal(12345)
count.value = 1

def increment():
    count.value += 1
"""
    compiler = WtfUICompiler()
    binary = compiler.compile(source)

    # Find position of first RET (marks end of first function)
    ret_pos = binary.find(bytes([OpCode.RET]))
    assert ret_pos != -1, "RET opcode not found - function not compiled"

    # Find position of first HALT
    halt_pos = binary.find(bytes([OpCode.HALT]))
    assert halt_pos != -1, "HALT opcode not found"

    # HALT must come BEFORE RET (main code halts before functions start)
    assert halt_pos < ret_pos, (
        f"Fallthrough bug: HALT at {halt_pos} comes after RET at {ret_pos}. "
        "Main code can fall through into function definitions."
    )


def test_compile_full_halts_before_functions():
    """compile_full() must also emit HALT before deferred functions.

    This ensures source maps are correctly generated with the fix.
    """
    source = """
count = Signal(12345)

def increment():
    count.value += 1
"""
    compiler = WtfUICompiler()
    # compile_full returns (binary, css, sourcemap) tuple
    binary, _css, _sourcemap = compiler.compile_full(source)

    ret_pos = binary.find(bytes([OpCode.RET]))
    halt_pos = binary.find(bytes([OpCode.HALT]))

    assert halt_pos < ret_pos, (
        f"compile_full fallthrough bug: HALT at {halt_pos} after RET at {ret_pos}"
    )


def test_compile_with_css_halts_before_functions():
    """compile_with_css() must also emit HALT before deferred functions."""
    source = """
count = Signal(12345)

def increment():
    count.value += 1
"""
    compiler = WtfUICompiler()
    binary, _css = compiler.compile_with_css(source)

    ret_pos = binary.find(bytes([OpCode.RET]))
    halt_pos = binary.find(bytes([OpCode.HALT]))

    assert halt_pos < ret_pos, (
        f"compile_with_css fallthrough bug: HALT at {halt_pos} after RET at {ret_pos}"
    )
