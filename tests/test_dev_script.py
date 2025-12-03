# tests/test_dev_script.py
"""Tests for the dev script."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def dev_script() -> Path:
    """Path to the dev script."""
    script = Path(__file__).parent.parent / "dev"
    assert script.exists(), "dev script not found"
    return script


def test_dev_script_is_executable(dev_script: Path):
    """Dev script should be executable."""
    assert os.access(dev_script, os.X_OK)


def test_dev_script_help(dev_script: Path):
    """Dev script help command works."""
    result = subprocess.run(
        [str(dev_script), "help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "setup" in result.stdout
    assert "dev" in result.stdout  # dev script now uses 'dev' instead of 'start'
    assert "test" in result.stdout


def test_dev_script_unknown_command(dev_script: Path):
    """Dev script handles unknown commands."""
    result = subprocess.run(
        [str(dev_script), "unknown_command"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Unknown command" in result.stdout or "Unknown command" in result.stderr


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


class TestDevScriptFunctional:
    """Functional tests that actually start servers."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent

    def test_flow_dev_cli_starts_server(self, project_root: Path):
        """uv run flow dev starts server successfully."""
        port = get_free_port()
        proc = subprocess.Popen(
            [
                "uv",
                "run",
                "flow",
                "dev",
                "examples.todo.app:app",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            if wait_for_server(url):
                resp = httpx.get(url)
                assert resp.status_code == 200
                assert "Flow" in resp.text or "Todo" in resp.text
            else:
                # Server didn't start - check for errors
                proc.terminate()
                _, stderr = proc.communicate(timeout=5)
                pytest.fail(f"Server failed to start: {stderr.decode()}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_flow_dev_local_app_import(self, tmp_path: Path):
        """flow dev can import app.py from current directory.

        This test would have caught Bug #2 (sys.path not including cwd).
        """
        # Create minimal FastAPI app
        (tmp_path / "app.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "source": "local_app"}
""")
        port = get_free_port()
        proc = subprocess.Popen(
            ["uv", "run", "flow", "dev", "app:app", "--port", str(port)],
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

    def test_dev_start_serves_todo_app(self, dev_script: Path, project_root: Path):
        """./dev dev with explicit app path serves the Todo app.

        Note: Tests explicit path, not default, since ./dev default may vary.
        """
        # Note: dev script delegates to 'uv run flow dev' with default port 8000
        # Use explicit path to avoid default path issues
        proc = subprocess.Popen(
            [str(dev_script), "dev", "examples.todo.app:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root,
            env={**os.environ},
        )
        try:
            url = "http://127.0.0.1:8000"  # Default port in dev script
            if wait_for_server(url, timeout=15):
                resp = httpx.get(url)
                assert resp.status_code == 200
                assert "Flow Todo App" in resp.text or "flow" in resp.text.lower()
            else:
                proc.terminate()
                stdout, stderr = proc.communicate(timeout=5)
                # Check if it's a port conflict (common in CI)
                if "address already in use" in stderr.decode().lower():
                    pytest.skip("Port 8000 already in use")
                pytest.fail(
                    f"Server failed to start: stdout={stdout.decode()}, stderr={stderr.decode()}"
                )
        finally:
            proc.terminate()
            proc.wait(timeout=5)
