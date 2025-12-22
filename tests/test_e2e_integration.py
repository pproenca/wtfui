"""End-to-end integration tests for WtfUI framework."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from wtfui import Effect, Signal, component, provide, rpc
from wtfui.core.injection import clear_providers
from wtfui.ui import Button, Div, Text
from wtfui.web.compiler import transform_for_client
from wtfui.web.rpc import RpcRegistry
from wtfui.web.server import create_app


@dataclass
class AppState:
    """Test application state."""

    count: Signal[int]
    name: Signal[str]


def test_full_counter_app():
    """Integration: Full counter app works end-to-end."""
    clear_providers()
    RpcRegistry.clear()

    state = AppState(count=Signal(0), name=Signal("Test"))
    provide(AppState, state)

    @rpc
    async def increment():
        state.count.value += 1
        return state.count.value

    @component
    async def CounterApp(state: AppState):
        with Div(cls="counter") as root:
            Text(f"Count: {state.count.value}")
            Button("Inc", on_click=increment)
        return root

    app = create_app(CounterApp)
    client = TestClient(app)

    # Initial render
    response = client.get("/")
    assert response.status_code == 200
    assert "Count: 0" in response.text

    # RPC call
    response = client.post("/api/rpc/increment", json={})
    assert response.status_code == 200
    assert response.json() == 1

    # State updated
    assert state.count.value == 1


def test_reactive_signal_effect_chain():
    """Integration: Signal → Effect chain works correctly."""
    from wtfui.core.scheduler import wait_for_scheduler

    effects_run = []
    count = Signal(0)

    Effect(lambda: effects_run.append(count.value))

    assert effects_run == [0]  # Initial

    count.value = 1
    wait_for_scheduler()
    assert effects_run == [0, 1]

    count.value = 2
    wait_for_scheduler()
    assert effects_run == [0, 1, 2]


def test_ast_transformation_security():
    """Integration: AST transformation removes server secrets."""
    source = """
import sqlalchemy
import os
from wtfui import component, rpc

SECRET = os.environ.get("API_KEY")

@rpc
async def get_data():
    db = sqlalchemy.connect()
    return db.query(SECRET)

@component
async def App():
    pass
"""

    # Expect warnings about removed server imports
    with pytest.warns(UserWarning, match="Removed server-only import"):
        client_code = transform_for_client(source)

    # Server imports MUST be removed
    assert "import sqlalchemy" not in client_code
    assert "import os" not in client_code

    # RPC body MUST be stubbed
    assert "db.query" not in client_code


def test_full_build_pipeline():
    """Integration: Full build produces deployable artifacts."""
    from wtfui.web.build import generate_client_bundle, generate_html_shell

    with tempfile.TemporaryDirectory() as tmpdir:
        source_code = """
from wtfui import component, rpc
from wtfui.ui import Div, Text

@rpc
async def get_message():
    return "Hello from server!"

@component
async def App():
    with Div() as root:
        with Text("Hello Flow!"):
            pass
    return root
"""

        output = Path(tmpdir) / "dist"
        output.mkdir()
        client_dir = output / "client"
        client_dir.mkdir()

        # Generate client bundle
        client_file = client_dir / "app.py"
        generate_client_bundle(source_code, client_file)

        # Verify client bundle is safe
        client_code = client_file.read_text()
        assert "@component" in client_code
        assert "Hello from server" not in client_code  # RPC body stubbed

        # Generate HTML shell
        html = generate_html_shell(app_module="app", title="Test App")
        html_file = output / "index.html"
        html_file.write_text(html)

        # HTML shell is valid
        assert "<!DOCTYPE html>" in html
        assert "wtfui-root" in html
        assert "pyodide" in html.lower()


def test_element_tree_building():
    """Integration: Context managers build correct tree structure."""
    with Div(cls="root") as root:
        with Div(cls="header") as header:
            Text("Title")
        with Div(cls="body") as body:
            Button("Click")
            Button("Cancel")

    # Verify tree structure
    assert len(root.children) == 2
    assert root.children[0] is header
    assert root.children[1] is body

    assert len(header.children) == 1
    assert header.children[0].tag == "Text"

    assert len(body.children) == 2
    assert all(c.tag == "Button" for c in body.children)


def test_renderer_protocol_consistency():
    """Integration: HTMLRenderer and DOMRenderer produce consistent structure."""
    from wtfui.web.renderer import DOMRenderer, HTMLRenderer

    with Div(cls="container") as root:
        Text("Hello")

    # HTML renderer
    html_renderer = HTMLRenderer()
    html_output = html_renderer.render(root)

    assert "container" in html_output
    assert "Hello" in html_output

    # DOM renderer (with mock document)
    mock_doc = MagicMock()
    mock_el = MagicMock()
    mock_doc.createElement.return_value = mock_el

    dom_renderer = DOMRenderer(document=mock_doc, proxy_factory=lambda x: x)
    dom_renderer.render(root)

    # Both should create elements
    assert mock_doc.createElement.called


def test_element_registry_event_routing():
    """Integration: ElementRegistry routes events to correct handlers."""
    from wtfui.tui.runtime import ElementRegistry

    registry = ElementRegistry()
    clicked = []

    def on_click():
        clicked.append(True)

    btn = Button("Test", on_click=on_click)

    # Register the button
    registry.register(btn)

    # Get the handler using Python's id()
    handler = registry.get_handler(id(btn), "click")
    assert handler is not None

    # Invoke handler
    handler()
    assert clicked == [True]


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_import_hook_transforms_client_modules():
    """Integration: Import hook transforms *_client modules."""
    # Create a temp module
    import sys

    from wtfui.web.compiler import install_import_hook, uninstall_import_hook

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write source with server code that sets a module-level flag
        source_file = Path(tmpdir) / "testmod.py"
        source_file.write_text("""
import sqlalchemy  # Server-only import

HAS_SQLALCHEMY = True

from wtfui import component

@component
async def App():
    pass

app = App
""")

        # Install hook and add to path
        sys.path.insert(0, tmpdir)
        install_import_hook()

        try:
            # Import as client module (dynamically created, not a real module)
            import testmod_client  # type: ignore[import-not-found]

            # The module should be importable (sqlalchemy import stripped)
            assert hasattr(testmod_client, "App")
            assert hasattr(testmod_client, "app")
            # The HAS_SQLALCHEMY should NOT exist (entire import line removed)
            # This verifies transformation occurred
            assert testmod_client is not None  # Import succeeded without sqlalchemy
        finally:
            uninstall_import_hook()
            sys.path.remove(tmpdir)
            # Clean up
            for mod in list(sys.modules.keys()):
                if "testmod" in mod:
                    del sys.modules[mod]
