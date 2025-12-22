"""Tests for SplitBrainAnalyzer.

Verifies that the analyzer correctly classifies modules as
CLIENT, SERVER, or SHARED based on their imports and decorators.
"""

import tempfile
from pathlib import Path

from wtfui.web.compiler.analyzer import ModuleType, SplitBrainAnalyzer
from wtfui.web.compiler.graph import DependencyGraph


def test_analyzer_creation():
    """SplitBrainAnalyzer can be instantiated."""
    graph = DependencyGraph()
    analyzer = SplitBrainAnalyzer(graph)
    assert analyzer.graph is graph


def test_classify_client_module():
    """Module with UI elements is classified as CLIENT."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            """
from wtfui.ui import Div, Text
from wtfui.core.signal import Signal

count = Signal(0)
with Div():
    Text("Hello")
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("app") == ModuleType.CLIENT


def test_classify_server_module_by_import():
    """Module importing server packages is classified as SERVER."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text(
            """
import os
import sqlite3
import subprocess
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("api") == ModuleType.SERVER


def test_classify_server_module_by_rpc():
    """Module with @rpc decorator is classified as SERVER."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text(
            """
from wtfui.web.rpc import rpc

@rpc
def fetch_users():
    return []
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("api") == ModuleType.SERVER


def test_classify_shared_module():
    """Pure utility module is classified as SHARED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "utils.py").write_text(
            """
def add(a, b):
    return a + b

def format_name(first, last):
    return f"{first} {last}"
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("utils") == ModuleType.SHARED


def test_get_client_modules():
    """get_client_modules returns all CLIENT modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "counter.py").write_text("from wtfui.core.signal import Signal")
        (root / "button.py").write_text("from wtfui.ui import Button")
        (root / "api.py").write_text("import os")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        clients = analyzer.get_client_modules()
        assert "counter" in clients
        assert "button" in clients
        assert "api" not in clients


def test_get_server_modules():
    """get_server_modules returns all SERVER modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "db.py").write_text("import sqlite3")
        (root / "files.py").write_text("import os")
        (root / "ui.py").write_text("from wtfui.ui import Div")

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        servers = analyzer.get_server_modules()
        assert "db" in servers
        assert "files" in servers
        assert "ui" not in servers


def test_detect_ui_elements_in_with():
    """Analyzer detects UI elements in with statements."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            """
with Div():
    with VStack():
        Text("Hello")
        Button("Click")
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("app") == ModuleType.CLIENT


def test_detect_signal_usage():
    """Analyzer detects Signal usage as CLIENT indicator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "counter.py").write_text(
            """
count = Signal(0)
count.value += 1
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        assert analyzer.get_type("counter") == ModuleType.CLIENT


def test_server_takes_priority():
    """SERVER classification takes priority over CLIENT."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Module with both client and server indicators
        (root / "mixed.py").write_text(
            """
import os
from wtfui.ui import Div

with Div():
    pass
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Server takes priority for security reasons
        assert analyzer.get_type("mixed") == ModuleType.SERVER


def test_unknown_module_is_shared():
    """Unknown modules default to SHARED."""
    graph = DependencyGraph()
    analyzer = SplitBrainAnalyzer(graph)
    analyzer.analyze()

    assert analyzer.get_type("nonexistent") == ModuleType.SHARED
