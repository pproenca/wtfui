"""Tests for @rpc function compilation to RPC_CALL opcode."""

import ast

from wtfui.web.compiler.linker import has_rpc_decorator
from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.wtfuibyte import WtfUICompiler


class TestRpcDecoratorDetection:
    """Tests for shared RPC decorator detection utility."""

    def test_detects_simple_rpc_decorator(self) -> None:
        """Detects @rpc decorated function."""
        source = """
@rpc
async def fetch_user(user_id: int) -> dict:
    return {"id": user_id}
"""
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, ast.AsyncFunctionDef)

        assert has_rpc_decorator(func) is True

    def test_ignores_function_without_rpc(self) -> None:
        """Non-decorated function returns False."""
        source = """
def regular_function():
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)

        assert has_rpc_decorator(func) is False

    def test_detects_rpc_with_other_decorators(self) -> None:
        """Detects @rpc even with other decorators."""
        source = """
@other_decorator
@rpc
async def multi_decorated():
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, ast.AsyncFunctionDef)

        assert has_rpc_decorator(func) is True


class TestWtfUICompilerRpcIntegration:
    """Tests for WtfUICompiler RPC function handling."""

    def test_accepts_rpc_functions_parameter(self) -> None:
        """WtfUICompiler accepts rpc_functions parameter."""
        rpc_funcs = {"fetch_user", "get_data"}
        compiler = WtfUICompiler(rpc_functions=rpc_funcs)

        assert compiler.rpc_functions == rpc_funcs

    def test_rpc_functions_defaults_to_none(self) -> None:
        """WtfUICompiler defaults rpc_functions to None."""
        compiler = WtfUICompiler()

        assert compiler.rpc_functions is None

    def test_combined_rpc_detection(self) -> None:
        """WtfUICompiler combines external rpc_functions with local scan."""
        # External RPC (from Linker in multi-module build)
        rpc_funcs = {"external_rpc_func"}
        compiler = WtfUICompiler(rpc_functions=rpc_funcs)

        # Should detect external_rpc_func as RPC even without seeing definition
        assert compiler._is_rpc_call("external_rpc_func") is True
        assert compiler._is_rpc_call("unknown_func") is False


class TestLocalRpcScanning:
    """Tests for local RPC function scanning during compilation."""

    def test_scan_populates_rpc_registry(self) -> None:
        """_scan_rpc_functions populates _rpc_registry with @rpc functions."""
        source = """
@rpc
async def fetch_data():
    return "data"

def regular_func():
    pass
"""
        tree = ast.parse(source)
        compiler = WtfUICompiler()
        compiler._scan_rpc_functions(tree)

        assert "fetch_data" in compiler._rpc_registry
        assert "regular_func" not in compiler._rpc_registry
        assert compiler._is_rpc_call("fetch_data") is True

    def test_scan_finds_multiple_rpc_functions(self) -> None:
        """Scanning finds all @rpc decorated functions."""
        source = """
@rpc
async def func_a():
    pass

@rpc
def func_b():
    pass

def not_rpc():
    pass
"""
        tree = ast.parse(source)
        compiler = WtfUICompiler()
        compiler._scan_rpc_functions(tree)

        assert len(compiler._rpc_registry) == 2
        assert compiler._is_rpc_call("func_a") is True
        assert compiler._is_rpc_call("func_b") is True
        assert compiler._is_rpc_call("not_rpc") is False


class TestRpcCallEmission:
    """Tests for RPC_CALL opcode emission."""

    def test_rpc_call_emits_opcode(self) -> None:
        """Calling @rpc function emits RPC_CALL opcode."""
        source = """
@rpc
async def get_user():
    return {"name": "test"}

get_user()
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # RPC_CALL opcode should be in bytecode
        assert OpCode.RPC_CALL.value in bytecode

    def test_rpc_signal_initialized_before_call(self) -> None:
        """Result signal is initialized before RPC_CALL (prevents undefined)."""
        source = """
@rpc
async def fetch_data():
    return "data"

fetch_data()
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Find INIT_SIG_STR and RPC_CALL positions
        init_pos = bytecode.find(bytes([OpCode.INIT_SIG_STR.value]))
        rpc_pos = bytecode.find(bytes([OpCode.RPC_CALL.value]))

        assert init_pos >= 0, "INIT_SIG_STR not found - signal not initialized"
        assert rpc_pos >= 0, "RPC_CALL not found"
        assert init_pos < rpc_pos, (
            f"Signal must be initialized BEFORE RPC_CALL. "
            f"INIT_SIG_STR at {init_pos}, RPC_CALL at {rpc_pos}"
        )

    def test_rpc_call_followed_by_load_sig(self) -> None:
        """RPC_CALL is followed by LOAD_SIG to maintain stack contract."""
        source = """
@rpc
async def fetch_data():
    return "data"

fetch_data()
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Find RPC_CALL position
        rpc_bytes = bytes([OpCode.RPC_CALL.value])
        rpc_pos = bytecode.find(rpc_bytes)
        assert rpc_pos >= 0, "RPC_CALL not found"

        # After RPC_CALL: u16 + u16 + u8 = 5 bytes, then LOAD_SIG
        # RPC_CALL format: [op:1][func_str_id:2][result_sig_id:2][argc:1] = 6 bytes total
        load_sig_pos = rpc_pos + 6
        assert bytecode[load_sig_pos] == OpCode.LOAD_SIG.value, (
            f"Expected LOAD_SIG (0x{OpCode.LOAD_SIG.value:02x}) at position {load_sig_pos}, "
            f"got 0x{bytecode[load_sig_pos]:02x}"
        )

    def test_rpc_call_with_arguments(self) -> None:
        """RPC call with arguments pushes args to stack first."""
        source = """
@rpc
async def add_numbers(a, b):
    return a + b

add_numbers(1, 2)
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Should contain PUSH_NUM for args and RPC_CALL
        assert bytes([OpCode.PUSH_NUM.value]) in bytecode
        assert bytes([OpCode.RPC_CALL.value]) in bytecode

    def test_rpc_call_bytecode_format(self) -> None:
        """RPC_CALL bytecode has correct format with ARGC."""
        source = """
@rpc
async def my_func(x):
    return x

my_func(42)
"""
        compiler = WtfUICompiler()
        bytecode = compiler.compile(source)

        # Find RPC_CALL opcode position
        rpc_pos = bytecode.find(bytes([OpCode.RPC_CALL.value]))
        assert rpc_pos >= 0

        # After opcode: u16 (func_str_id) + u16 (sig_id) + u8 (argc=1)
        argc_pos = rpc_pos + 5  # 1 + 2 + 2 = 5
        assert bytecode[argc_pos] == 1, f"Expected argc=1, got {bytecode[argc_pos]}"
