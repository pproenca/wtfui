"""Flow Wasm - Browser-side execution via Pyodide/Emscripten."""

from flow.wasm.bootstrap import (
    FlowApp,
    get_document,
    get_pyodide,
    mount,
)
from flow.wasm.platform import (
    get_platform,
    is_browser,
    is_pyodide,
    is_server,
)

__all__ = [
    "FlowApp",
    "get_document",
    "get_platform",
    "get_pyodide",
    "is_browser",
    "is_pyodide",
    "is_server",
    "mount",
]
