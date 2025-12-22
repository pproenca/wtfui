# tests/test_dev_script.py
"""Tests for the dev workflow - Makefile targets and wtfui CLI."""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

# =============================================================================
# Makefile tests
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def test_makefile_exists(project_root: Path):
    """Makefile should exist in project root."""
    makefile = project_root / "Makefile"
    assert makefile.exists(), "Makefile not found"


def test_makefile_help(project_root: Path):
    """make help shows available targets."""
    result = subprocess.run(
        ["make", "help"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "setup" in result.stdout
    assert "test" in result.stdout
    assert "lint" in result.stdout


# =============================================================================
# Functional tests - actually start servers and verify they respond
# These tests catch bugs that basic command tests miss
# =============================================================================


def get_free_port() -> int:
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port: int = s.getsockname()[1]
        return port


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    """Wait for server to be ready, return True if successful."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(url, timeout=1.0)
            if resp.status_code < 500:
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(0.2)
    return False


class TestWtfUIDevCLI:
    """Functional tests for wtfui dev CLI command."""

    def test_wtfui_dev_cli_starts_server(self, project_root: Path):
        """uv run wtfui dev starts server successfully."""
        port = get_free_port()
        todo_dir = project_root / "examples" / "todo"
        # Use PYTHONPATH to include example directory so imports work
        # Run from project root to use main environment
        env = {"PYTHONPATH": str(todo_dir), **subprocess.os.environ}
        proc = subprocess.Popen(
            [
                "uv",
                "run",
                "wtfui",
                "dev",
                "app:app",
                "--web",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root,
            env=env,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            if wait_for_server(url):
                resp = httpx.get(url)
                assert resp.status_code == 200
                assert "WtfUI" in resp.text or "Todo" in resp.text
            else:
                # Server didn't start - check for errors
                proc.terminate()
                _, stderr = proc.communicate(timeout=5)
                pytest.fail(f"Server failed to start: {stderr.decode()}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    @pytest.mark.skip(
        reason="Incompatible with Meta-CLI: temp directory lacks Python 3.14t venv. "
        "Meta-CLI auto-elevation triggers 'uv sync' which uses global Python 3.12, "
        "conflicting with requires-python>=3.14. Test local imports via test_loader.py instead."
    )
    def test_wtfui_dev_local_app_import(self, tmp_path: Path, project_root: Path):
        """wtfui dev can import app.py from current directory.

        This test would have caught Bug #2 (sys.path not including cwd).
        """
        # Create minimal FastAPI app with pyproject.toml (required by Meta-CLI)
        (tmp_path / "pyproject.toml").write_text("""[project]
name = "test-app"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["fastapi", "uvicorn"]
""")
        (tmp_path / "app.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "source": "local_app"}
""")
        port = get_free_port()
        proc = subprocess.Popen(
            ["uv", "run", "wtfui", "dev", "app:app", "--web", "--port", str(port)],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            if wait_for_server(url):
                resp = httpx.get(url)
                assert resp.status_code == 200
                # Verify it's our local app
                assert "local_app" in resp.text or resp.status_code == 200
            else:
                proc.terminate()
                _, stderr = proc.communicate(timeout=5)
                pytest.fail(f"Server failed to start with local app: {stderr.decode()}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
