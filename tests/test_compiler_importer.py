"""Tests for zero-build import hook."""

import os
import sys
import tempfile
from pathlib import Path

from flow.compiler.importer import (
    FlowImportHook,
    install_import_hook,
    set_debug_mode,
    uninstall_import_hook,
)


def test_import_hook_can_be_installed():
    """Import hook can be added to sys.meta_path."""
    initial_count = len(sys.meta_path)

    install_import_hook()
    try:
        assert len(sys.meta_path) == initial_count + 1
        assert any(isinstance(f, FlowImportHook) for f in sys.meta_path)
    finally:
        uninstall_import_hook()

    assert len(sys.meta_path) == initial_count


def test_import_hook_caches_transformations():
    """Import hook caches transformed modules for performance."""
    install_import_hook()
    try:
        hook = next(f for f in sys.meta_path if isinstance(f, FlowImportHook))
        assert hasattr(hook, "_cache")
    finally:
        uninstall_import_hook()


def test_import_hook_respects_debug_env():
    """Import hook respects FLOW_DEBUG environment variable."""
    original = os.environ.get("FLOW_DEBUG")
    try:
        os.environ["FLOW_DEBUG"] = "1"
        hook = FlowImportHook()
        assert hook._debug_mode is True
    finally:
        if original is None:
            os.environ.pop("FLOW_DEBUG", None)
        else:
            os.environ["FLOW_DEBUG"] = original


def test_debug_mode_can_be_set_programmatically():
    """Debug mode can be enabled via function call."""
    set_debug_mode(True)
    hook = FlowImportHook()
    assert hook._debug_mode is True
    set_debug_mode(False)


def test_import_hook_handles_client_suffix():
    """Import hook handles *_client module pattern."""
    install_import_hook()
    try:
        hook = next(f for f in sys.meta_path if isinstance(f, FlowImportHook))

        # Create a temp file to test finding
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "myapp.py"
            test_file.write_text("""
from flow import component
@component
async def App():
    pass
""")

            # Hook should find myapp.py when looking for myapp_client
            spec = hook.find_spec("myapp_client", [tmpdir])
            assert spec is not None
            assert spec.origin is not None
            assert "myapp.py" in spec.origin

    finally:
        uninstall_import_hook()


def test_import_hook_ignores_non_client_modules():
    """Import hook ignores modules without _client suffix."""
    install_import_hook()
    try:
        hook = next(f for f in sys.meta_path if isinstance(f, FlowImportHook))

        # Regular imports should return None (not handled)
        spec = hook.find_spec("json", None)
        assert spec is None

        spec = hook.find_spec("flow.signal", None)
        assert spec is None

    finally:
        uninstall_import_hook()
