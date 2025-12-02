"""Flow Wasm - Browser-side execution via Pyodide/Emscripten."""

from flow.wasm.platform import (
    get_platform,
    is_browser,
    is_pyodide,
    is_server,
)

__all__ = [
    "get_platform",
    "is_browser",
    "is_pyodide",
    "is_server",
]
