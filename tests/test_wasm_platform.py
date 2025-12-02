"""Tests for Wasm platform detection."""

import sys
from unittest import mock

from flow.wasm.platform import (
    get_platform,
    is_browser,
    is_pyodide,
    is_server,
)


def test_is_server_on_standard_cpython():
    """Standard CPython reports as server."""
    # In tests, we're running on CPython
    assert is_server() is True


def test_is_browser_on_cpython():
    """Standard CPython is not a browser."""
    assert is_browser() is False


def test_is_pyodide_on_cpython():
    """Standard CPython is not Pyodide."""
    assert is_pyodide() is False


def test_get_platform_on_cpython():
    """get_platform returns 'server' on CPython."""
    assert get_platform() == "server"


def test_pyodide_detection_with_mock():
    """Pyodide is detected when 'pyodide' module exists."""
    with mock.patch.dict(sys.modules, {"pyodide": mock.MagicMock()}):
        assert is_pyodide() is True
        assert is_browser() is True
        assert get_platform() == "browser"


def test_emscripten_detection_with_mock():
    """Emscripten is detected via sys.platform."""
    with mock.patch.object(sys, "platform", "emscripten"):
        assert is_browser() is True
        assert get_platform() == "browser"


def test_wasi_detection_with_mock():
    """WASI is detected but treated as server (headless Wasm)."""
    with mock.patch.object(sys, "platform", "wasi"):
        assert is_browser() is False
        assert get_platform() == "wasi"
