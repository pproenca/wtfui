"""Tests for WtfUIByte server endpoints."""

import pytest
from fastapi.testclient import TestClient

from wtfui.web.compiler.writer import MAGIC_HEADER
from wtfui.web.server.app import create_app


@pytest.fixture
def wtfuibyte_client():
    """Create test client with WtfUIByte support."""

    # Create a simple component for testing
    async def simple_app():
        from wtfui.core.signal import Signal
        from wtfui.ui.elements import Div, Text

        count = Signal(0)
        with Div() as root:
            Text(f"Count: {count.value}")
        return root

    app = create_app(simple_app)
    return TestClient(app)


class TestWtfUIByteEndpoint:
    """Test /app.mfbc endpoint."""

    def test_wtfuibyte_endpoint_returns_binary(self, wtfuibyte_client) -> None:
        """GET /app.mfbc returns WtfUIByte binary."""
        response = wtfuibyte_client.get("/app.mfbc")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_wtfuibyte_starts_with_magic_header(self, wtfuibyte_client) -> None:
        """Binary starts with MYFU magic header."""
        response = wtfuibyte_client.get("/app.mfbc")

        assert response.content.startswith(MAGIC_HEADER)

    def test_wtfuibyte_cache_control(self, wtfuibyte_client) -> None:
        """Binary has appropriate cache headers for dev."""
        response = wtfuibyte_client.get("/app.mfbc")

        # In dev mode, should have no-cache or short cache
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache, must-revalidate"
