"""Tests for FlowByte server endpoints."""

import pytest
from fastapi.testclient import TestClient

from flow.compiler.writer import MAGIC_HEADER
from flow.server.app import create_app


@pytest.fixture
def flowbyte_client():
    """Create test client with FlowByte support."""

    # Create a simple component for testing
    async def simple_app():
        from flow.signal import Signal
        from flow.ui.elements import Div, Text

        count = Signal(0)
        with Div() as root:
            Text(f"Count: {count.value}")
        return root

    app = create_app(simple_app)
    return TestClient(app)


class TestFlowByteEndpoint:
    """Test /app.fbc endpoint."""

    def test_flowbyte_endpoint_returns_binary(self, flowbyte_client) -> None:
        """GET /app.fbc returns FlowByte binary."""
        response = flowbyte_client.get("/app.fbc")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_flowbyte_starts_with_magic_header(self, flowbyte_client) -> None:
        """Binary starts with FLOW magic header."""
        response = flowbyte_client.get("/app.fbc")

        assert response.content.startswith(MAGIC_HEADER)

    def test_flowbyte_cache_control(self, flowbyte_client) -> None:
        """Binary has appropriate cache headers for dev."""
        response = flowbyte_client.get("/app.fbc")

        # In dev mode, should have no-cache or short cache
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache, must-revalidate"
