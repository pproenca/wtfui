"""Tests for BoundarySentinel security firewall.

Verifies that the sentinel correctly detects and reports
security violations when client code imports server modules.
"""

import tempfile
from pathlib import Path

import pytest

from wtfui.web.compiler.analyzer import SplitBrainAnalyzer
from wtfui.web.compiler.graph import DependencyGraph
from wtfui.web.compiler.validator import (
    BoundarySentinel,
    BoundarySentinelError,
    SecurityViolation,
)


def test_sentinel_creation():
    """BoundarySentinel can be instantiated."""
    graph = DependencyGraph()
    analyzer = SplitBrainAnalyzer(graph)
    analyzer.analyze()

    sentinel = BoundarySentinel(graph, analyzer)
    assert sentinel.graph is graph
    assert sentinel.analyzer is analyzer


def test_no_violations_for_valid_code():
    """No violations when client only imports shared modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "utils.py").write_text("def add(a, b): return a + b")
        (root / "ui.py").write_text(
            """
import utils
from wtfui.ui import Div
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        assert len(violations) == 0


def test_detect_client_importing_server():
    """Detects when client module imports server module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text("import os")  # SERVER
        (root / "ui.py").write_text(
            """
import api
from wtfui.ui import Div
"""
        )  # CLIENT importing SERVER

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        assert len(violations) == 1
        assert violations[0].client_module == "ui"
        assert violations[0].server_module == "api"


def test_validate_raises_on_violation():
    """validate() raises BoundarySentinelError on violations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text("import sqlite3")  # SERVER
        (root / "ui.py").write_text(
            """
import api
from wtfui.ui import Div
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        with pytest.raises(BoundarySentinelError) as exc_info:
            sentinel.validate()

        assert len(exc_info.value.violations) == 1


def test_multiple_violations():
    """Detects multiple security violations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "db.py").write_text("import sqlite3")  # SERVER
        (root / "files.py").write_text("import os")  # SERVER
        (root / "ui.py").write_text(
            """
import db
import files
from wtfui.ui import Div
"""
        )  # CLIENT importing 2 SERVERs

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        assert len(violations) == 2


def test_check_single_module():
    """check_single checks only one module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text("import os")
        (root / "ui.py").write_text(
            """
import api
from wtfui.ui import Div
"""
        )
        (root / "other.py").write_text(
            """
import api
from wtfui.ui import Button
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        # Only check "ui" module
        violations = sentinel.check_single("ui")
        assert len(violations) == 1
        assert violations[0].client_module == "ui"


def test_get_allowed_imports_for_client():
    """get_allowed_imports filters out server modules for client."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text("import os")  # SERVER
        (root / "utils.py").write_text("pass")  # SHARED
        (root / "ui.py").write_text(
            """
import api
import utils
from wtfui.ui import Div
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        allowed = sentinel.get_allowed_imports("ui")
        assert "utils" in allowed
        assert "api" not in allowed


def test_get_rpc_candidates():
    """get_rpc_candidates returns server modules that need RPC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "api.py").write_text("import os")  # SERVER
        (root / "db.py").write_text("import sqlite3")  # SERVER
        (root / "utils.py").write_text("pass")  # SHARED
        (root / "ui.py").write_text(
            """
import api
import db
import utils
from wtfui.ui import Div
"""
        )

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        rpc_needed = sentinel.get_rpc_candidates("ui")
        assert "api" in rpc_needed
        assert "db" in rpc_needed
        assert "utils" not in rpc_needed


def test_server_can_import_server():
    """Server modules can freely import other server modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "db.py").write_text("import sqlite3")  # SERVER
        (root / "api.py").write_text(
            """
import db
import os
"""
        )  # SERVER importing SERVER - OK

        graph = DependencyGraph()
        graph.build_parallel(root)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        assert len(violations) == 0


def test_security_violation_str():
    """SecurityViolation has readable string representation."""
    violation = SecurityViolation(
        client_module="ui",
        server_module="api",
        message="Client module 'ui' cannot import server module 'api'",
    )

    assert "ui" in str(violation)
    assert "api" in str(violation)


def test_error_message_formatting():
    """BoundarySentinelError has formatted error message."""
    violations = [
        SecurityViolation(
            client_module="ui",
            server_module="api",
            message="Error 1",
        ),
        SecurityViolation(
            client_module="ui",
            server_module="db",
            message="Error 2",
        ),
    ]

    error = BoundarySentinelError(violations)
    message = str(error)

    assert "Bundle boundary violations" in message
    assert "Error 1" in message
    assert "Error 2" in message


def test_boundary_sentinel_docstrings_describe_optimization():
    """Verify docstrings describe bundle optimization, not security claims."""
    import wtfui.web.compiler.analyzer as analyzer_module
    import wtfui.web.compiler.validator as validator_module
    from wtfui.web.compiler.validator import BoundarySentinel

    # Module docstrings should describe bundle optimization
    assert (
        "bundle" in validator_module.__doc__.lower()
        or "optimization" in validator_module.__doc__.lower()
    ), "validator.py docstring should mention bundle optimization"
    assert (
        "bundle" in analyzer_module.__doc__.lower()
        or "optimization" in analyzer_module.__doc__.lower()
    ), "analyzer.py docstring should mention bundle optimization"

    # Docstrings should NOT claim this IS a security mechanism
    # (but may explain what it's NOT for clarity)
    validator_doc = validator_module.__doc__.lower()
    assert "security firewall" not in validator_doc, (
        "validator.py should not claim to be a security firewall"
    )
    assert "critical for security" not in validator_doc, (
        "validator.py should not claim to be critical for security"
    )

    # Class docstring should describe optimization, not security
    sentinel_doc = BoundarySentinel.__doc__.lower()
    assert (
        "bundle" in sentinel_doc
        or "optimization" in sentinel_doc
        or "code splitting" in sentinel_doc
    ), "BoundarySentinel docstring should describe bundle optimization"
    assert "security firewall" not in sentinel_doc, (
        "BoundarySentinel should not claim to be a security firewall"
    )
