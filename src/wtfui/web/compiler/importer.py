import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from wtfui.web.compiler.transformer import compile_for_client, transform_for_client

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import CodeType, ModuleType

_debug_mode: bool = False
_debug_output_dir: Path = Path(".fuse-debug")
_settings_lock = threading.Lock()


def set_debug_mode(enabled: bool, output_dir: Path | None = None) -> None:
    global _debug_mode, _debug_output_dir
    with _settings_lock:
        _debug_mode = enabled
        if output_dir is not None:
            _debug_output_dir = output_dir


def get_debug_output_dir() -> Path:
    return _debug_output_dir


def _is_debug_enabled() -> bool:
    return _debug_mode or os.environ.get("WTFUI_DEBUG", "").lower() in (
        "1",
        "true",
        "yes",
    )


class WtfUIImportHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()
        self._debug_mode = _is_debug_enabled()

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        _target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.endswith("_client"):
            return None

        original_name = fullname[:-7]

        parts = original_name.split(".")
        filename = parts[-1] + ".py"

        search_paths = list(path) if path else sys.path

        for search_path in search_paths:
            original_path = Path(search_path) / filename
            if original_path.exists():
                return importlib.machinery.ModuleSpec(
                    name=fullname,
                    loader=self,
                    origin=str(original_path),
                )

        return None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType | None:
        del spec
        return None

    def exec_module(self, module: ModuleType) -> None:
        spec = getattr(module, "__spec__", None)
        if spec is None or spec.origin is None:
            msg = f"Cannot load module without origin: {module}"
            raise ImportError(msg)

        origin_path = Path(spec.origin)

        with self._lock:
            cache_key = str(origin_path)
            mtime = origin_path.stat().st_mtime

            cached = self._cache.get(cache_key)
            if cached and cached[0] == mtime:
                code = cached[1]
            else:
                source = origin_path.read_text(encoding="utf-8")
                code = compile_for_client(source, str(origin_path))
                self._cache[cache_key] = (mtime, code)

                if self._debug_mode:
                    self._dump_debug_output(spec.name, origin_path, source)

        exec(cast("CodeType", code), module.__dict__)  # noqa: S102

    def _dump_debug_output(self, module_name: str, origin_path: Path, original_source: str) -> None:
        try:
            debug_dir = get_debug_output_dir()
            debug_dir.mkdir(parents=True, exist_ok=True)

            transformed = transform_for_client(original_source)

            debug_file = debug_dir / f"{module_name}.py"
            debug_content = f"""# WTFUI DEBUG OUTPUT
# ==================
# Original file: {origin_path}
# Module name: {module_name}
# Generated at: {datetime.now().isoformat()}
#
# Transformations applied:
#   - Removed server-only imports
#   - Stubbed @rpc function bodies
#   - Preserved @component functions and client code
# ==================

{transformed}
"""
            debug_file.write_text(debug_content)
            print(f"[WTFUI DEBUG] {debug_file}", file=sys.stderr)

        except Exception as e:
            print(f"[WTFUI DEBUG] Warning: {e}", file=sys.stderr)


_import_hook: WtfUIImportHook | None = None
_install_lock = threading.Lock()


def install_import_hook(debug: bool = False) -> None:
    global _import_hook

    if debug:
        set_debug_mode(True)

    with _install_lock:
        if _import_hook is not None:
            return
        _import_hook = WtfUIImportHook()
        sys.meta_path.insert(0, _import_hook)


def uninstall_import_hook() -> None:
    global _import_hook

    with _install_lock:
        if _import_hook is not None:
            sys.meta_path.remove(_import_hook)
            _import_hook = None
