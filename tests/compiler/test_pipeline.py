"""Pipeline integration tests for WtfUIByte compiler.

Tests the complete compilation pipeline:
    Source → AST → Graph → Analyzer → Validator → Compiler → .mfbc

Validates that all components work together correctly.
"""

import tempfile
from pathlib import Path

from wtfui.web.compiler import (
    ArtifactCache,
    CSSGenerator,
    DependencyGraph,
    Linker,
    ModuleType,
    OpCode,
    SplitBrainAnalyzer,
    compile_to_wtfuibyte,
)
from wtfui.web.compiler.evaluator import DYNAMIC_STYLE, safe_eval_style
from wtfui.web.compiler.validator import BoundarySentinel


def test_simple_signal_compilation():
    """Compile simple signal initialization."""
    source = """
count = Signal(0)
"""
    bytecode = compile_to_wtfuibyte(source)

    assert bytecode.startswith(b"MYFU")
    assert OpCode.INIT_SIG_NUM.to_bytes(1, "big") in bytecode


def test_signal_increment_compilation():
    """Compile signal increment with stack operations."""
    source = """
count = Signal(0)
count.value += 1
"""
    bytecode = compile_to_wtfuibyte(source)

    # Should use stack-based operations
    assert OpCode.LOAD_SIG.to_bytes(1, "big") in bytecode
    assert OpCode.PUSH_NUM.to_bytes(1, "big") in bytecode
    assert OpCode.ADD_STACK.to_bytes(1, "big") in bytecode
    assert OpCode.STORE_SIG.to_bytes(1, "big") in bytecode


def test_dom_element_compilation():
    """Compile DOM element with context manager."""
    source = """
with Div(class_="container"):
    Text("Hello")
"""
    bytecode = compile_to_wtfuibyte(source)

    assert OpCode.DOM_CREATE.to_bytes(1, "big") in bytecode
    assert OpCode.DOM_APPEND.to_bytes(1, "big") in bytecode
    assert OpCode.DOM_TEXT.to_bytes(1, "big") in bytecode
    assert OpCode.DOM_ATTR_CLASS.to_bytes(1, "big") in bytecode


def test_static_style_compilation():
    """Static styles emit DOM_STYLE_STATIC opcodes."""
    source = """
with Div(style={"background": "blue", "padding": "4px"}):
    Text("Styled")
"""
    bytecode = compile_to_wtfuibyte(source)

    assert OpCode.DOM_STYLE_STATIC.to_bytes(1, "big") in bytecode


def test_intrinsic_compilation():
    """Intrinsic calls compile to CALL_INTRINSIC."""
    source = """
count = Signal(10)
print("Count:", count.value)
"""
    bytecode = compile_to_wtfuibyte(source)

    assert OpCode.CALL_INTRINSIC.to_bytes(1, "big") in bytecode


def test_dependency_graph_integration():
    """DependencyGraph builds module graph from source files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create module structure
        (root / "app.py").write_text("""
from components import Button
from utils import format_date
""")
        (root / "components.py").write_text("""
from utils import helper
""")
        (root / "utils.py").write_text("""
def helper():
    pass
def format_date():
    pass
""")

        graph = DependencyGraph()
        graph.build_parallel(root)

        # Module names are stored without .py extension
        assert "app" in graph.nodes
        assert "components" in graph.nodes
        assert "utils" in graph.nodes


def test_analyzer_integration():
    """SplitBrainAnalyzer classifies modules correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create client module (imports flow.ui - detected by CLIENT_INDICATORS)
        (root / "client.py").write_text("""
from wtfui.ui import Div, Text
from wtfui.core.signal import Signal
count = Signal(0)
with Div():
    Text("Hello")
""")

        # Create server module (uses os/pathlib - detected by SERVER_INDICATORS)
        (root / "server.py").write_text("""
import os
from pathlib import Path
def get_data():
    return {"items": [1, 2, 3]}
""")

        # Create shared module (no indicators)
        (root / "shared.py").write_text("""
def format_number(n):
    return f"{n:,}"
""")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Module names without .py extension
        assert analyzer.get_type("client") == ModuleType.CLIENT
        assert analyzer.get_type("server") == ModuleType.SERVER
        assert analyzer.get_type("shared") == ModuleType.SHARED


def test_validator_integration():
    """BoundarySentinel detects security violations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create client module that imports from server module
        (root / "client.py").write_text("""
from server import secret_function
from wtfui.ui import Div
from wtfui.core.signal import Signal
""")

        # Create server module with server-only imports
        (root / "server.py").write_text("""
import os
from pathlib import Path
def secret_function():
    pass
""")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        validator = BoundarySentinel(graph, analyzer)
        violations = validator.check()

        # Check violations (client imports server)
        assert len(violations) > 0
        assert any("client" in str(v) for v in violations)


def test_linker_integration():
    """Linker identifies RPC calls correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create client module
        (root / "client.py").write_text("""
from server import fetch_data
result = fetch_data()
""")

        # Create server module
        (root / "server.py").write_text("""
from wtfui.web.rpc import rpc
@rpc
def fetch_data():
    return []
""")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("client.py")

        # Should identify RPC endpoint
        assert len(result.rpc_calls) > 0 or len(linker.get_all_rpc_endpoints()) > 0


def test_cache_integration():
    """ArtifactCache stores and retrieves bytecode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("count = Signal(0)")

        # Compile
        bytecode = compile_to_wtfuibyte(source_file.read_text())

        # Cache
        cache = ArtifactCache()
        cache.save(source_file, bytecode)

        # Retrieve
        cached = cache.load(source_file)
        assert cached == bytecode
        assert cache.is_valid(source_file)


def test_css_generator_integration():
    """CSSGenerator produces valid CSS from style dicts."""
    css = CSSGenerator()

    # Register some styles
    cls1 = css.register({"bg": "#3b82f6", "p": 4, "rounded": 8})
    cls2 = css.register({"display": "flex", "justify": "center", "items": "center"})

    output = css.get_output()

    # Verify CSS output
    assert f".{cls1}" in output
    assert f".{cls2}" in output
    assert "background-color:#3b82f6" in output
    assert "display:flex" in output


def test_evaluator_with_compiler():
    """Evaluator integrates with compiler for style detection."""
    import ast

    # Static style
    static_node = ast.parse("{'background': 'blue'}", mode="eval").body
    result = safe_eval_style(static_node)
    assert isinstance(result, dict)
    assert result["background"] == "blue"

    # Dynamic style
    dynamic_node = ast.parse("get_style()", mode="eval").body
    result = safe_eval_style(dynamic_node)
    assert result is DYNAMIC_STYLE


def test_full_pipeline_simple_app():
    """Full pipeline test with simple app."""
    import warnings

    source = """
# Simple counter app
count = Signal(0)

def increment():
    count.value += 1

with Div(class_="container"):
    with Div(style={"background": "#3b82f6", "padding": "16px"}):
        Text("Counter")

    Button("+", on_click=increment)
"""
    # Compile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bytecode = compile_to_wtfuibyte(source)

    # Verify bytecode structure
    assert bytecode.startswith(b"MYFU")

    # Verify opcodes present
    assert OpCode.INIT_SIG_NUM.to_bytes(1, "big") in bytecode
    assert OpCode.DOM_CREATE.to_bytes(1, "big") in bytecode
    assert OpCode.DOM_STYLE_STATIC.to_bytes(1, "big") in bytecode
    assert OpCode.HALT.to_bytes(1, "big") in bytecode


def test_pipeline_with_theme_colors():
    """Pipeline handles theme color references."""
    import ast

    # Theme color reference should be resolved statically
    node = ast.parse("Colors.Blue._500", mode="eval").body
    dict_node = ast.Dict(keys=[ast.Constant("bg")], values=[node])

    result = safe_eval_style(dict_node)
    assert isinstance(result, dict)
    assert result["bg"] == "#3b82f6"


def test_pipeline_cache_persistence():
    """Cache can be persisted and restored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = Signal(1)")
        cache_dir = Path(tmpdir) / ".wtfuicache"

        bytecode = compile_to_wtfuibyte(source_file.read_text())

        # Save to cache
        cache1 = ArtifactCache()
        cache1.save(source_file, bytecode)
        cache1.persist(cache_dir)

        # Restore to new cache
        cache2 = ArtifactCache()
        restored = cache2.restore(cache_dir)

        assert restored == 1
        assert cache2.load(source_file) == bytecode
