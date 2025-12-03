"""Tests for Linker - RPC resolution and function call resolution.

Verifies that the Linker correctly identifies function calls
and determines whether they should be direct calls or RPC calls.
"""

import tempfile
from pathlib import Path

from flow.compiler.analyzer import SplitBrainAnalyzer
from flow.compiler.graph import DependencyGraph
from flow.compiler.linker import FunctionRef, Linker, LinkResult


def test_linker_creation():
    """Linker can be instantiated."""
    graph = DependencyGraph()
    analyzer = SplitBrainAnalyzer(graph)
    analyzer.analyze()

    linker = Linker(graph, analyzer)
    assert linker.graph is graph


def test_detect_intrinsic_calls():
    """Linker detects intrinsic function calls (print, len, etc.)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            """
print("Hello")
x = len([1, 2, 3])
s = str(42)
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("app")

        assert len(result.intrinsic_calls) == 3
        intrinsic_names = {call.name for call in result.intrinsic_calls}
        assert "print" in intrinsic_names
        assert "len" in intrinsic_names
        assert "str" in intrinsic_names


def test_detect_local_function_calls():
    """Linker detects local function calls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            """
def helper():
    return 42

def main():
    x = helper()
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("app")

        # helper() call in main()
        local_names = {call.name for call in result.local_calls}
        assert "helper" in local_names


def test_detect_rpc_calls():
    """Linker detects calls to @rpc decorated functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text(
            """
from flow.rpc import rpc

@rpc
def fetch_data():
    return []
"""
        )
        (root / "ui.py").write_text(
            """
import api
from flow.ui import Div

result = api.fetch_data()
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("ui")

        # fetch_data should be identified as RPC
        rpc_names = {call.name for call in result.rpc_calls}
        assert "fetch_data" in rpc_names


def test_detect_server_module_calls():
    """Linker marks calls to server module functions as RPC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "db.py").write_text(
            """
import sqlite3

def get_users():
    return []
"""
        )
        (root / "ui.py").write_text(
            """
import db
from flow.ui import Div

users = db.get_users()
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("ui")

        # get_users is in server module, should be RPC
        rpc_names = {call.name for call in result.rpc_calls}
        assert "get_users" in rpc_names


def test_get_all_rpc_endpoints():
    """get_all_rpc_endpoints returns all functions needing RPC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text(
            """
from flow.rpc import rpc

@rpc
def endpoint1():
    pass

@rpc
def endpoint2():
    pass

def private_helper():
    pass
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        endpoints = linker.get_all_rpc_endpoints()

        assert "api" in endpoints
        func_names = {f.name for f in endpoints["api"]}
        assert "endpoint1" in func_names
        assert "endpoint2" in func_names


def test_generate_rpc_stub():
    """generate_rpc_stub creates JavaScript fetch code."""
    ref = FunctionRef(
        name="fetch_users",
        module="myapp.api",
        is_rpc=True,
    )

    graph = DependencyGraph()
    analyzer = SplitBrainAnalyzer(graph)
    analyzer.analyze()

    linker = Linker(graph, analyzer)
    stub = linker.generate_rpc_stub(ref)

    assert "async function fetch_users" in stub
    assert "fetch('/api/rpc/myapp.api.fetch_users'" in stub
    assert "method: 'POST'" in stub


def test_function_ref_properties():
    """FunctionRef correctly stores function metadata."""
    ref = FunctionRef(
        name="my_func",
        module="myapp",
        is_rpc=True,
        is_intrinsic=False,
    )

    assert ref.name == "my_func"
    assert ref.module == "myapp"
    assert ref.is_rpc is True
    assert ref.is_intrinsic is False


def test_link_result_properties():
    """LinkResult correctly categorizes function calls."""
    result = LinkResult(module_name="test")

    result.intrinsic_calls.append(FunctionRef("print", "__builtins__", is_intrinsic=True))
    result.rpc_calls.append(FunctionRef("fetch", "api", is_rpc=True))
    result.local_calls.append(FunctionRef("helper", "test"))

    assert len(result.intrinsic_calls) == 1
    assert len(result.rpc_calls) == 1
    assert len(result.local_calls) == 1


def test_shared_module_calls_not_rpc():
    """Calls to shared module functions are not RPC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "utils.py").write_text(
            """
def format_date(d):
    return str(d)
"""
        )
        (root / "ui.py").write_text(
            """
import utils
from flow.ui import Div

formatted = utils.format_date("2024-01-01")
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("ui")

        # format_date is in shared module, should be local call
        local_names = {call.name for call in result.local_calls}
        rpc_names = {call.name for call in result.rpc_calls}

        assert "format_date" in local_names
        assert "format_date" not in rpc_names


def test_empty_module():
    """Linker handles empty modules gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "empty.py").write_text("pass")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("empty")

        assert len(result.intrinsic_calls) == 0
        assert len(result.rpc_calls) == 0
        assert len(result.local_calls) == 0
