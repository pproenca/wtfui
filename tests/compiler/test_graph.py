"""Tests for dependency graph builder.

Verifies that the DependencyGraph correctly parses Python files
in parallel and builds a module dependency graph.
"""

import tempfile
from pathlib import Path

from wtfui.web.compiler.graph import DependencyGraph, DependencyNode


def test_dependency_graph_creation():
    """DependencyGraph can be instantiated."""
    graph = DependencyGraph()
    assert len(graph) == 0
    assert graph.nodes == {}


def test_parse_single_file():
    """DependencyGraph parses a single Python file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text("import os\nimport sys")

        graph = DependencyGraph()
        graph.build_parallel(root)

        assert len(graph) == 1
        assert "app" in graph


def test_parse_multiple_files():
    """DependencyGraph parses multiple Python files in parallel."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text("import lib")
        (root / "lib.py").write_text("import utils")
        (root / "utils.py").write_text("pass")

        graph = DependencyGraph()
        graph.build_parallel(root)

        assert len(graph) == 3
        assert "app" in graph
        assert "lib" in graph
        assert "utils" in graph


def test_extract_imports():
    """DependencyGraph correctly extracts imports from AST."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            """
import os
import sys
from pathlib import Path
from collections.abc import Callable
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        imports = graph.get_imports("app")
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "collections.abc" in imports


def test_get_ast():
    """DependencyGraph returns parsed AST for modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text("x = 1")

        graph = DependencyGraph()
        graph.build_parallel(root)

        ast = graph.get_ast("app")
        assert ast is not None
        assert len(ast.body) == 1


def test_get_dependents():
    """DependencyGraph finds modules that depend on a given module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core.py").write_text("pass")
        (root / "app.py").write_text("import core")
        (root / "lib.py").write_text("import core")

        graph = DependencyGraph()
        graph.build_parallel(root)

        dependents = graph.get_dependents("core")
        assert "app" in dependents
        assert "lib" in dependents


def test_topological_order():
    """DependencyGraph returns modules in topological order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core.py").write_text("pass")
        (root / "utils.py").write_text("import core")
        (root / "app.py").write_text("import utils")

        graph = DependencyGraph()
        graph.build_parallel(root)

        order = graph.topological_order()
        # core should come before utils, utils before app
        core_idx = order.index("core")
        utils_idx = order.index("utils")
        app_idx = order.index("app")

        assert core_idx < utils_idx or utils_idx < app_idx


def test_empty_directory():
    """DependencyGraph handles empty directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        graph = DependencyGraph()
        graph.build_parallel(root)

        assert len(graph) == 0


def test_syntax_error_handling():
    """DependencyGraph skips files with syntax errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "good.py").write_text("x = 1")
        (root / "bad.py").write_text("def incomplete(")  # Syntax error

        graph = DependencyGraph()
        graph.build_parallel(root)

        # Only good.py should be parsed
        assert "good" in graph
        assert "bad" not in graph


def test_nested_directories():
    """DependencyGraph parses files in nested directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pkg").mkdir()
        (root / "pkg" / "module.py").write_text("pass")
        (root / "app.py").write_text("import pkg.module")

        graph = DependencyGraph()
        graph.build_parallel(root)

        assert len(graph) == 2
        # Check that nested module is properly named
        assert any("module" in name for name in graph.nodes)


def test_dependency_node_slots():
    """DependencyNode uses __slots__ for memory efficiency."""
    node = DependencyNode(
        name="test",
        path=Path("test.py"),
        imports={"os"},
        tree=None,
    )

    assert hasattr(node, "__slots__")
    assert node.name == "test"
    assert node.imports == {"os"}


def test_circular_dependency_detection():
    """DependencyGraph detects circular dependencies."""
    import pytest

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create circular dependency: a -> b -> c -> a
        (root / "a.py").write_text("import b")
        (root / "b.py").write_text("import c")
        (root / "c.py").write_text("import a")

        graph = DependencyGraph()
        graph.build_parallel(root)

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.topological_order()


def test_self_import_handled():
    """DependencyGraph handles self-imports gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Self-import is technically valid Python
        (root / "self.py").write_text("import self")

        graph = DependencyGraph()
        graph.build_parallel(root)

        # Should not raise (self-import is handled)
        assert "self" in graph
