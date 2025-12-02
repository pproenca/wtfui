"""
Import Hook for Zero-Build Development.

Registers a sys.meta_path finder that intercepts imports of
'*_client' modules and transforms them on-the-fly.

Per MANIFEST.md Tenet III: "python app.py must be the only command
required to start a full-stack dev environment."

DEBUG MODE:
    Set FLOW_DEBUG=1 to dump transformed source to .flow-debug/
    This helps troubleshoot AST transformation issues.

Usage:
    from flow.compiler.importer import install_import_hook
    install_import_hook()

    # Now 'import myapp_client' will:
    # 1. Find 'myapp.py'
    # 2. Transform via ClientSafeTransformer
    # 3. Execute transformed bytecode
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from types import CodeType
from typing import TYPE_CHECKING, cast

from flow.compiler.transformer import compile_for_client, transform_for_client

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType


# Global debug settings
_debug_mode: bool = False
_debug_output_dir: Path = Path(".flow-debug")
_settings_lock = threading.Lock()


def set_debug_mode(enabled: bool, output_dir: Path | None = None) -> None:
    """Enable or disable debug mode for import hook."""
    global _debug_mode, _debug_output_dir
    with _settings_lock:
        _debug_mode = enabled
        if output_dir is not None:
            _debug_output_dir = output_dir


def get_debug_output_dir() -> Path:
    """Get the current debug output directory."""
    return _debug_output_dir


def _is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _debug_mode or os.environ.get("FLOW_DEBUG", "").lower() in (
        "1",
        "true",
        "yes",
    )


class FlowImportHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """
    Import hook that transforms '*_client' modules on-the-fly.

    When you import 'myapp_client', this finder:
    1. Looks for 'myapp.py' in the same directory
    2. Reads the source
    3. Runs ClientSafeTransformer
    4. Compiles and executes the transformed bytecode

    No physical file is created - everything happens in memory.
    """

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
        """Find module spec for '*_client' modules."""
        # Only handle modules ending in '_client'
        if not fullname.endswith("_client"):
            return None

        # Derive the original module name
        original_name = fullname[:-7]  # Remove '_client' suffix

        # Handle dotted names (e.g., mypackage.myapp_client)
        parts = original_name.split(".")
        filename = parts[-1] + ".py"

        # Try to find the original .py file
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

    def create_module(self, _spec: importlib.machinery.ModuleSpec) -> None:
        """Use default module creation."""
        return None

    def exec_module(self, module: ModuleType) -> None:
        """Execute the transformed module."""
        spec = getattr(module, "__spec__", None)
        if spec is None or spec.origin is None:
            msg = f"Cannot load module without origin: {module}"
            raise ImportError(msg)

        origin_path = Path(spec.origin)

        with self._lock:
            # Check cache by mtime
            cache_key = str(origin_path)
            mtime = origin_path.stat().st_mtime

            cached = self._cache.get(cache_key)
            if cached and cached[0] == mtime:
                code = cached[1]
            else:
                # Read and transform
                source = origin_path.read_text(encoding="utf-8")
                code = compile_for_client(source, str(origin_path))
                self._cache[cache_key] = (mtime, code)

                # DEBUG MODE: Dump transformed source
                if self._debug_mode:
                    self._dump_debug_output(spec.name, origin_path, source)

        # Execute in module's namespace
        exec(cast(CodeType, code), module.__dict__)  # noqa: S102

    def _dump_debug_output(self, module_name: str, origin_path: Path, original_source: str) -> None:
        """Dump transformed source to disk for debugging."""
        try:
            debug_dir = get_debug_output_dir()
            debug_dir.mkdir(parents=True, exist_ok=True)

            transformed = transform_for_client(original_source)

            debug_file = debug_dir / f"{module_name}.py"
            debug_content = f"""# FLOW DEBUG OUTPUT
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
            print(f"[FLOW DEBUG] {debug_file}", file=sys.stderr)

        except Exception as e:
            print(f"[FLOW DEBUG] Warning: {e}", file=sys.stderr)


# Singleton instance
_import_hook: FlowImportHook | None = None


def install_import_hook(debug: bool = False) -> None:
    """Install the Flow import hook for zero-build development."""
    global _import_hook

    if debug:
        set_debug_mode(True)

    if _import_hook is not None:
        return  # Already installed

    _import_hook = FlowImportHook()
    sys.meta_path.insert(0, _import_hook)


def uninstall_import_hook() -> None:
    """Remove the Flow import hook."""
    global _import_hook

    if _import_hook is not None:
        sys.meta_path.remove(_import_hook)
        _import_hook = None
