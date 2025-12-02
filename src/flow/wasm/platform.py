"""Platform detection for Universal Runtime.

Per MANIFEST.md Tenet V: "Universal Isomorphism means a Single-Source Codebase."

Flow code runs on multiple targets:
- Server: Standard CPython (3.14+ with No-GIL)
- Browser: Pyodide (CPython compiled to Wasm) or Emscripten
- WASI: WebAssembly System Interface (headless Wasm, no browser)

This module detects the runtime environment to conditionally:
- Use appropriate renderer (HTMLRenderer vs DOMRenderer)
- Enable/disable certain features (file I/O, networking)
- Optimize for the target (No-GIL threading vs single-threaded Wasm)
"""

from __future__ import annotations

import sys
from typing import Literal

# Platform types
Platform = Literal["server", "browser", "wasi"]


def is_pyodide() -> bool:
    """Check if running in Pyodide (Python-in-browser via Wasm).

    Pyodide provides JavaScript interop through the 'pyodide' module
    and 'js' module for direct DOM access.
    """
    return "pyodide" in sys.modules


def is_browser() -> bool:
    """Check if running in a browser environment.

    Returns True for:
    - Pyodide (Python compiled to Wasm, runs in browser)
    - Emscripten builds (via sys.platform == 'emscripten')
    """
    if is_pyodide():
        return True
    return sys.platform == "emscripten"


def is_server() -> bool:
    """Check if running on a server (standard CPython).

    Returns True when NOT running in browser or WASI.
    """
    return not is_browser() and sys.platform != "wasi"


def get_platform() -> Platform:
    """Get the current platform identifier.

    Returns:
        'server': Standard CPython on server
        'browser': Pyodide or Emscripten in browser
        'wasi': WebAssembly System Interface (headless)
    """
    if is_browser():
        return "browser"
    if sys.platform == "wasi":
        return "wasi"
    return "server"
