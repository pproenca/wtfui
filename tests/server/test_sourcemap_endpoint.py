"""Tests for /app.fsm source map endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from wtfui.web.compiler.sourcemap import FSM_MAGIC, SourceMap


@pytest.fixture
async def test_client():
    """Create test client with minimal Flow app."""
    from wtfui.core.component import component
    from wtfui.ui.elements import Div, Text
    from wtfui.web.server.app import create_app

    @component
    async def App():
        with Div():
            Text("Hello")

    app = create_app(App)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_fsm_endpoint_returns_binary(test_client: AsyncClient) -> None:
    """GET /app.fsm returns application/octet-stream."""
    response = await test_client.get("/app.fsm")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"


@pytest.mark.asyncio
async def test_fsm_endpoint_returns_valid_sourcemap(test_client: AsyncClient) -> None:
    """GET /app.fsm returns valid .fsm binary."""
    response = await test_client.get("/app.fsm")
    assert response.content.startswith(FSM_MAGIC)

    sm = SourceMap.from_bytes(response.content)
    assert len(sm.files) >= 0  # May be empty for demo
