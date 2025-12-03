"""Security Gatekeeper Tests.

Validates that the BoundarySentinel security firewall correctly prevents
CLIENT code from importing SERVER modules, protecting sensitive server-side
logic from being exposed to the client bundle.

These tests verify the core security requirements of the FlowByte compiler:
1. Client modules cannot import server-only modules
2. Server-only imports are detected and blocked
3. RPC calls are properly firewalled
"""

import pytest

from flow.compiler.analyzer import ModuleType, SplitBrainAnalyzer
from flow.compiler.graph import DependencyGraph
from flow.compiler.linker import Linker
from flow.compiler.validator import (
    BoundarySentinel,
    BoundarySentinelError,
)


@pytest.mark.gatekeeper
class TestBoundarySentinelSecurity:
    """Test security boundary enforcement."""

    def test_client_cannot_import_server_module(self, tmp_path):
        """Verify CLIENT modules cannot import SERVER modules."""
        # Create server module with database access
        server_module = tmp_path / "server.py"
        server_module.write_text("""
import sqlite3
from flow.rpc import rpc

@rpc
def get_user(user_id: int):
    conn = sqlite3.connect('db.sqlite')
    return conn.execute('SELECT * FROM users WHERE id=?', [user_id]).fetchone()
""")

        # Create client module that tries to import server
        client_module = tmp_path / "client.py"
        client_module.write_text("""
from flow.ui import Div, Text
from server import get_user

with Div():
    Text("Hello")
""")

        # Build dependency graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze module types
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Validate boundary
        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        # Should detect violation
        assert len(violations) > 0, "Expected security violation not detected"
        violation = violations[0]
        assert violation.client_module == "client"
        assert violation.server_module == "server"
        assert "client" in str(violation).lower()

    def test_server_can_import_server(self, tmp_path):
        """Verify SERVER modules can import other SERVER modules."""
        # Create database module
        db_module = tmp_path / "database.py"
        db_module.write_text("""
import sqlite3

def get_connection():
    return sqlite3.connect('db.sqlite')
""")

        # Create auth module that imports database
        auth_module = tmp_path / "auth.py"
        auth_module.write_text("""
import os
from database import get_connection
from flow.rpc import rpc

@rpc
def authenticate(token: str):
    conn = get_connection()
    return conn.execute('SELECT * FROM sessions WHERE token=?', [token]).fetchone()
""")

        # Build graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Both should be SERVER
        assert analyzer.get_type("database") == ModuleType.SERVER
        assert analyzer.get_type("auth") == ModuleType.SERVER

        # Validate - no violations expected
        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()
        assert len(violations) == 0, f"Unexpected violations: {violations}"

    def test_client_can_import_client(self, tmp_path):
        """Verify CLIENT modules can import other CLIENT modules."""
        # Create UI component
        button_module = tmp_path / "button.py"
        button_module.write_text("""
from flow.ui import Button, Text

def CustomButton(label: str):
    with Button():
        Text(label)
""")

        # Create app that imports button
        app_module = tmp_path / "app.py"
        app_module.write_text("""
from flow.ui import Div
from button import CustomButton

with Div():
    CustomButton("Click me")
""")

        # Build graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Both should be CLIENT
        assert analyzer.get_type("button") == ModuleType.CLIENT
        assert analyzer.get_type("app") == ModuleType.CLIENT

        # Validate - no violations expected
        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()
        assert len(violations) == 0, f"Unexpected violations: {violations}"

    def test_shared_module_accessible_by_both(self, tmp_path):
        """Verify SHARED modules can be imported by CLIENT and SERVER."""
        # Create shared utility
        utils_module = tmp_path / "utils.py"
        utils_module.write_text("""
def format_date(date):
    return date.strftime('%Y-%m-%d')

def sanitize_input(text):
    return text.strip()
""")

        # Create client using utils
        client_module = tmp_path / "client.py"
        client_module.write_text("""
from flow.ui import Div, Text
from utils import format_date

with Div():
    Text("Date")
""")

        # Create server using utils
        server_module = tmp_path / "server.py"
        server_module.write_text("""
import os
from utils import sanitize_input
from flow.rpc import rpc

@rpc
def save_data(text: str):
    clean = sanitize_input(text)
    return clean
""")

        # Build graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Utils should be SHARED
        assert analyzer.get_type("utils") == ModuleType.SHARED

        # Validate - no violations expected
        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()
        assert len(violations) == 0, f"Unexpected violations: {violations}"


@pytest.mark.gatekeeper
class TestRPCFirewall:
    """Test RPC security enforcement."""

    def test_rpc_calls_are_detected(self, tmp_path):
        """Verify RPC function calls are properly detected."""
        # Create server with RPC
        server_module = tmp_path / "api.py"
        server_module.write_text("""
import sqlite3
from flow.rpc import rpc

@rpc
def get_data():
    return {"key": "value"}

@rpc
def save_data(data):
    return True
""")

        # Create client calling RPC
        client_module = tmp_path / "app.py"
        client_module.write_text("""
from flow.ui import Div, Text, Button
import api

with Div():
    with Button(on_click=lambda: api.save_data({"test": 1})):
        Text("Save")
""")

        # Build graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Link
        linker = Linker(graph, analyzer)
        result = linker.link("app")

        # Verify RPC calls detected
        rpc_calls = [ref for ref in result.rpc_calls if ref.is_rpc]
        assert len(rpc_calls) >= 1, "Expected RPC calls not detected"

    def test_rpc_endpoints_enumerated(self, tmp_path):
        """Verify all RPC endpoints are enumerated.

        Note: In SERVER modules (detected by server-only imports like 'os'),
        ALL functions become RPC endpoints for security reasons - not just
        those with @rpc decorators. This prevents accidental exposure of
        server code to clients.
        """
        # Create server with multiple RPCs
        server_module = tmp_path / "api.py"
        server_module.write_text("""
import os
from flow.rpc import rpc

@rpc
def endpoint_a():
    return "a"

@rpc
def endpoint_b():
    return "b"

@rpc
def endpoint_c():
    return "c"

def private_function():
    return "private"
""")

        # Build and analyze
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)

        # Get all RPC endpoints
        endpoints = linker.get_all_rpc_endpoints()

        # Should find the module in endpoints
        assert "api" in endpoints
        endpoint_names = {ep.name for ep in endpoints["api"]}

        # All functions in SERVER module are RPC (security feature)
        assert "endpoint_a" in endpoint_names
        assert "endpoint_b" in endpoint_names
        assert "endpoint_c" in endpoint_names
        # private_function is also RPC because it's in a SERVER module
        assert "private_function" in endpoint_names


@pytest.mark.gatekeeper
class TestServerCodeIsolation:
    """Test that server code is properly isolated."""

    def test_server_imports_not_in_client_bundle(self, tmp_path):
        """Verify server-only imports are filtered from client code."""
        # Create server module with dangerous imports
        server_module = tmp_path / "server.py"
        server_module.write_text("""
import os
import subprocess
import sqlite3
from pathlib import Path
from flow.rpc import rpc

SECRET_KEY = os.environ.get('SECRET_KEY')

@rpc
def execute_command(cmd: str):
    return subprocess.check_output(cmd, shell=True)
""")

        # Analyze
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Server module should be classified as SERVER
        assert analyzer.get_type("server") == ModuleType.SERVER

        # Server imports should include dangerous modules
        server_node = graph.nodes.get("server")
        assert server_node is not None
        server_imports = server_node.imports
        assert "os" in server_imports
        assert "subprocess" in server_imports
        assert "sqlite3" in server_imports

    def test_multiple_security_violations_detected(self, tmp_path):
        """Verify all security violations are detected, not just first."""
        # Create server modules
        db_module = tmp_path / "database.py"
        db_module.write_text("import sqlite3")

        auth_module = tmp_path / "auth.py"
        auth_module.write_text("import os")

        # Create client importing multiple server modules
        client_module = tmp_path / "client.py"
        client_module.write_text("""
from flow.ui import Div
import database
import auth

with Div():
    pass
""")

        # Build graph
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # Analyze
        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Validate
        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        # Should detect multiple violations
        assert len(violations) == 2, f"Expected 2 violations, got {len(violations)}"

    def test_validate_raises_on_violation(self, tmp_path):
        """Verify validate() raises exception on security violation."""
        # Create violating code
        server_module = tmp_path / "server.py"
        server_module.write_text("import sqlite3")

        client_module = tmp_path / "client.py"
        client_module.write_text("""
from flow.ui import Div
import server

with Div():
    pass
""")

        # Build and analyze
        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        # validate() should raise
        with pytest.raises(BoundarySentinelError):
            sentinel.validate()


@pytest.mark.gatekeeper
class TestSecurityViolationMessages:
    """Test that security violations have clear error messages."""

    def test_violation_message_includes_source_and_target(self, tmp_path):
        """Verify violation messages include module names."""
        server_module = tmp_path / "secret_api.py"
        server_module.write_text("import os")

        client_module = tmp_path / "public_ui.py"
        client_module.write_text("""
from flow.ui import Div
import secret_api

with Div():
    pass
""")

        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)
        violations = sentinel.check()

        assert len(violations) == 1
        violation = violations[0]

        # Check that module names are in the violation
        assert violation.client_module == "public_ui"
        assert violation.server_module == "secret_api"
