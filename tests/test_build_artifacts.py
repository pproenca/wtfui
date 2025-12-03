"""Tests for build artifacts generation."""

import tempfile
from pathlib import Path

import pytest

from flow.build.artifacts import (
    generate_client_bundle,
    generate_html_shell,
    generate_pyodide_loader,
)


def test_generate_client_bundle_creates_file():
    """generate_client_bundle creates transformed Python file."""
    source = """
from flow import component
from flow.ui import Div

@component
async def App():
    with Div():
        pass
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "client.py"
        generate_client_bundle(source, output)

        assert output.exists()
        content = output.read_text()
        assert "@component" in content


def test_generate_client_bundle_removes_server_code():
    """generate_client_bundle strips server-only code."""
    source = """
import sqlalchemy
from flow import component, rpc

@rpc
async def get_data():
    return sqlalchemy.query()

@component
async def App():
    pass
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "client.py"
        # Expect warning about removed server import
        with pytest.warns(UserWarning, match="Removed server-only import"):
            generate_client_bundle(source, output)

        content = output.read_text()
        assert "import sqlalchemy" not in content


def test_generate_html_shell_has_pyodide_script():
    """generate_html_shell includes Pyodide loader script."""
    html = generate_html_shell(app_module="myapp")

    assert "pyodide" in html.lower()
    assert "<script" in html


def test_generate_html_shell_has_container():
    """generate_html_shell includes flow-root container."""
    html = generate_html_shell(app_module="myapp")

    assert "flow-root" in html


def test_generate_html_shell_has_import_statement():
    """generate_html_shell imports the app module."""
    html = generate_html_shell(app_module="counter_app")

    assert "counter_app" in html


def test_generate_pyodide_loader_returns_js():
    """generate_pyodide_loader creates JavaScript code."""
    js = generate_pyodide_loader(app_module="myapp", packages=["numpy"])

    assert "loadPyodide" in js
    assert "myapp" in js
    # Optional packages
    assert "numpy" in js


def test_generate_pyodide_loader_default_packages():
    """generate_pyodide_loader works without extra packages."""
    js = generate_pyodide_loader(app_module="myapp")

    assert "loadPyodide" in js
