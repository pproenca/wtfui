"""E2E test fixtures."""

from __future__ import annotations

import socket
import subprocess
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


def get_free_port() -> int:
    """Get a free port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture(scope="module")
def todo_server() -> Generator[str]:
    """Start todo app server for testing."""
    port = get_free_port()
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "examples.todo.app:app", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)  # Wait for server to start
    yield f"http://localhost:{port}"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def dashboard_server() -> Generator[str]:
    """Start dashboard app server for testing."""
    port = get_free_port()
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "examples.dashboard.app:app", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    yield f"http://localhost:{port}"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="function")
def chat_server() -> Generator[str]:
    """Start chat app server for testing.

    Uses function scope to ensure each test gets fresh server state,
    since the chat app uses module-level Signals that persist between requests.
    """
    port = get_free_port()
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "examples.chat.app:app", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    yield f"http://localhost:{port}"
    proc.terminate()
    proc.wait()
