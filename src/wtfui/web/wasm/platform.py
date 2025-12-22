import sys
from typing import Literal

Platform = Literal["server", "browser", "wasi"]


def is_pyodide() -> bool:
    return "pyodide" in sys.modules


def is_browser() -> bool:
    if is_pyodide():
        return True
    return sys.platform == "emscripten"


def is_server() -> bool:
    return not is_browser() and sys.platform != "wasi"


def get_platform() -> Platform:
    if is_browser():
        return "browser"
    if sys.platform == "wasi":
        return "wasi"
    return "server"
