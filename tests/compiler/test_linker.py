"""Tests for Linker - RPC resolution and function call resolution.

Verifies that the Linker correctly identifies function calls
and determines whether they should be direct calls or RPC calls.
"""

import tempfile
import warnings
from pathlib import Path

from wtfui.web.compiler.analyzer import SplitBrainAnalyzer
from wtfui.web.compiler.graph import DependencyGraph
from wtfui.web.compiler.linker import FunctionRef, Linker, LinkResult
from wtfui.web.compiler.shaker import CallGraph


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
from wtfui.web.rpc import rpc

@rpc
def fetch_data():
    return []
"""
        )
        (root / "ui.py").write_text(
            """
import api
from wtfui.ui import Div

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
from wtfui.ui import Div

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
from wtfui.web.rpc import rpc

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
from wtfui.ui import Div

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


class TestLinkerTreeShaking:
    """Test linker integration with tree shaking."""

    def test_filter_functions_removes_unreachable(self) -> None:
        """filter_functions removes functions not reachable from entry."""
        source = """
def helper():
    pass

def unused():
    pass

def App():
    helper()
"""
        graph = CallGraph.from_source(source)
        all_funcs = {"helper", "unused", "App"}

        from wtfui.web.compiler.linker import filter_unreachable

        kept = filter_unreachable(all_funcs, graph, entry="App")

        assert "App" in kept
        assert "helper" in kept
        assert "unused" not in kept

    def test_filter_preserves_rpc_endpoints(self) -> None:
        """RPC endpoints are preserved even if not called."""
        source = """
def App():
    pass
"""
        graph = CallGraph.from_source(source)
        all_funcs = {"App", "get_users"}  # get_users is RPC
        rpc_funcs = {"get_users"}

        from wtfui.web.compiler.linker import filter_unreachable

        kept = filter_unreachable(all_funcs, graph, entry="App", preserve=rpc_funcs)

        assert "get_users" in kept

    def test_filter_warns_on_dynamic_dispatch(self) -> None:
        """Warning issued when dynamic dispatch detected."""
        source = """
def dangerous():
    getattr(mod, name)()

def App():
    dangerous()
"""
        graph = CallGraph.from_source(source)

        from wtfui.web.compiler.linker import filter_unreachable

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            filter_unreachable({"App", "dangerous"}, graph, entry="App")

            # Should have warning about dynamic dispatch
            assert len(w) == 1
            assert "dynamic dispatch" in str(w[0].message).lower()
