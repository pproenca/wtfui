import importlib
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def load_app_component(app_path: str) -> Callable[[], Any]:
    if _is_file_path(app_path):
        return _load_from_file(app_path)
    else:
        return _load_from_module(app_path)


def _is_file_path(app_path: str) -> bool:
    if "/" in app_path or "\\" in app_path:
        return True

    base = app_path.split(":")[0]
    return base.endswith(".py")


def _load_from_module(app_path: str) -> Callable[[], Any]:
    if ":" not in app_path:
        app_path = f"{app_path}:app"

    module_path, attr_name = app_path.rsplit(":", 1)

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise ImportError(f"Cannot import module '{module_path}': {e}") from e

    if not hasattr(module, attr_name):
        raise AttributeError(f"Module '{module_path}' has no attribute '{attr_name}'")

    return getattr(module, attr_name)


def _load_from_file(app_path: str) -> Callable[[], Any]:
    if ":" in app_path and not app_path.startswith("/"):
        parts = app_path.rsplit(":", 1)
        if len(parts) == 2 and not Path(app_path).exists():
            file_path, attr_name = parts
        else:
            file_path = app_path
            attr_name = "app"
    else:
        file_path = app_path
        attr_name = "app"

    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"App file not found: {file_path}")

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    parent_dir = str(path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise ImportError(f"Cannot load module from {file_path}")

    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, attr_name):
        raise AttributeError(f"Module '{file_path}' has no attribute '{attr_name}'")

    return getattr(module, attr_name)
