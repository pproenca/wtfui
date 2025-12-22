"""Gatekeeper: Client Bundle Size & Purity.

Enforces Tenet VI (Security Firewall) and Tenet II (Isomorphism)
by ensuring server code is stripped and client code is tiny.

Thresholds:
- Bundle size: < 50KB for user code portion
- Security: Zero leakage of server libraries
"""

import warnings

import pytest

from wtfui.web.compiler.transformer import transform_for_client

# Mock App Source with forbidden imports
MOCK_APP_WITH_SERVER_CODE = '''\
"""Test app with server-only code."""

from wtfui import component, rpc
from wtfui.ui.elements import Div, Text

# Server-side: These should NOT appear in client bundle
import sqlite3  # Server-only stdlib


@rpc
async def get_secret_data() -> str:
    """Server-only RPC function."""
    # This entire function body should be stripped
    conn = sqlite3.connect(":memory:")
    return "secret_from_db"


@component
async def App():
    """Client component - should be preserved."""
    with Div(cls="container") as root:
        with Text("Hello Flow"):
            pass
    return root


app = App
'''


@pytest.mark.gatekeeper
def test_ghost_bundle_audit() -> None:
    """
    Gatekeeper: Client Bundle Size & Purity.

    Thresholds:
    - Size: < 50KB for generated client code
    - Purity: No server-only imports in client bundle

    Tests the AST transformer directly for security guarantees.
    """
    MAX_SIZE_KB = 50

    # Transform the source code (what build does internally)
    # Suppress expected UserWarning about removed server-only imports
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Removed server-only import")
        content = transform_for_client(MOCK_APP_WITH_SERVER_CODE)

    # 1. PURITY CHECK (Security)
    # These terms should be stripped from client bundle
    forbidden_terms = [
        "sqlite3",
        "secret_from_db",
        "conn = sqlite3",
    ]

    for term in forbidden_terms:
        assert term not in content, (
            f"Security Breach! Found '{term}' in client bundle.\n"
            f"Bundle content:\n{content[:500]}..."
        )

    # 2. PRESERVATION CHECK
    # These should still be in the client bundle
    required_terms = [
        "App",  # Component name
        "Div",  # UI element
        "Text",  # UI element
    ]

    for term in required_terms:
        assert term in content, f"Missing required term '{term}' in client bundle"

    # 3. SIZE CHECK (Performance)
    size_bytes = len(content.encode("utf-8"))
    size_kb = size_bytes / 1024

    print(f"\n[Ghost Gatekeeper] Bundle Size: {size_kb:.2f} KB ({size_bytes} bytes)")

    # Strict limit for the user code portion
    assert size_kb < MAX_SIZE_KB, f"Bundle Bloated! {size_kb:.2f}KB > {MAX_SIZE_KB}KB"


@pytest.mark.gatekeeper
def test_rpc_functions_become_stubs() -> None:
    """Verify @rpc decorated functions are replaced with fetch stubs."""
    rpc_app = '''\
from wtfui import component, rpc
from wtfui.ui.elements import Div
import os

@rpc
async def server_compute(x: int, y: int) -> int:
    """This computation happens on server."""
    return x + y + int(os.getenv("MAGIC", "0"))

@component
async def App():
    with Div() as root:
        pass
    return root

app = App
'''

    # Suppress expected UserWarning about removed server-only imports
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Removed server-only import")
        content = transform_for_client(rpc_app)

    # Server implementation details should be gone
    # Note: the import os is removed by SERVER_ONLY_MODULES
    assert "import os" not in content
    assert "os.getenv" not in content
    assert "MAGIC" not in content

    # RPC function should now have pass body (stub)
    assert "async def server_compute" in content

    print("\n[Ghost Gatekeeper] RPC stub verified")
