from wtfui.web.wasm.bootstrap import (
    WtfUIApp,
    get_document,
    get_pyodide,
    mount,
)
from wtfui.web.wasm.platform import (
    get_platform,
    is_browser,
    is_pyodide,
    is_server,
)

__all__ = [
    "WtfUIApp",
    "get_document",
    "get_platform",
    "get_pyodide",
    "is_browser",
    "is_pyodide",
    "is_server",
    "mount",
]
