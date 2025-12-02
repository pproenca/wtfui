# tests/test_server_app.py
"""Tests for FastAPI server integration."""

from fastapi.testclient import TestClient

from flow.component import component
from flow.server.app import create_app
from flow.ui import Div, Text


@component
async def SimpleApp():
    with Div(cls="container") as root, Text("Hello from Flow!"):
        pass
    return root


def test_create_app_returns_fastapi():
    """create_app returns a FastAPI instance."""
    app = create_app(SimpleApp)
    assert app is not None
    assert hasattr(app, "routes")


def test_app_serves_html_on_root():
    """App serves HTML on GET /."""
    app = create_app(SimpleApp)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hello from Flow!" in response.text


def test_app_has_websocket_endpoint():
    """App exposes /ws WebSocket endpoint."""
    app = create_app(SimpleApp)

    # Check that route exists
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/ws" in routes
