# tests/test_integration.py
"""End-to-End integration tests for Flow Framework."""

import asyncio

from fastapi.testclient import TestClient

from flow import Computed, Effect, Signal, component
from flow.injection import clear_providers, provide
from flow.renderer import HTMLRenderer
from flow.rpc import RpcRegistry, rpc
from flow.server import create_app
from flow.ui import Button, Div, Text


class TestCoreReactivity:
    """Test core reactivity system integration."""

    def test_signal_effect_computed_chain(self):
        """Signals, Effects, and Computed work together."""
        count = Signal(0)
        doubled = Computed(lambda: count.value * 2)

        # Verify initial values
        assert count.value == 0
        assert doubled() == 0

        # Update signal
        count.value = 5

        # Computed is invalidated and re-computes
        assert doubled() == 10

        # Effect tracks signal changes
        effect_values = []

        def track_count():
            effect_values.append(count.value)

        Effect(track_count)
        assert effect_values == [5]  # Initial run captures current value

        count.value = 10
        assert 10 in effect_values  # Effect re-ran


class TestUIRendering:
    """Test UI rendering integration."""

    def test_component_renders_to_html(self):
        """Full component renders to HTML string."""

        @component
        async def Counter():
            count = Signal(0)
            with Div(cls="counter") as root:
                with Text(f"Count: {count.value}"):
                    pass
                with Button(label="Increment"):
                    pass
            return root

        root = asyncio.run(Counter())
        renderer = HTMLRenderer()
        html = renderer.render(root)

        assert "counter" in html
        assert "Count:" in html
        assert "Increment" in html


class TestDependencyInjection:
    """Test dependency injection integration."""

    def test_component_with_injected_state(self):
        """Component receives injected dependencies."""
        clear_providers()

        class AppState:
            def __init__(self) -> None:
                self.user = Signal("Guest")

        state = AppState()
        provide(AppState, state)

        received = None

        @component
        async def Greeting(state: AppState):
            nonlocal received
            received = state.user.value

        asyncio.run(Greeting())
        assert received == "Guest"


class TestServerIntegration:
    """Test server integration."""

    def test_full_app_serves_html(self):
        """Full app with component serves HTML."""
        RpcRegistry.clear()

        @component
        async def App():
            with Div(cls="app") as root, Text("Hello, Flow!"):
                pass
            return root

        app = create_app(App)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "Hello, Flow!" in response.text
        assert "flow-root" in response.text

    def test_rpc_with_component(self):
        """RPC functions work alongside components."""
        RpcRegistry.clear()

        @rpc
        async def get_message() -> str:
            return "Server says hello!"

        @component
        async def App():
            with Div() as root:
                pass
            return root

        app = create_app(App)
        client = TestClient(app)

        response = client.post("/api/rpc/get_message", json={})

        assert response.status_code == 200
        assert response.json() == "Server says hello!"


class TestElementHierarchy:
    """Test element hierarchy building."""

    def test_nested_elements_build_tree(self):
        """Nested with blocks build correct tree."""
        with Div(cls="outer") as outer:
            with Div(cls="inner1"), Text("A"):
                pass
            with Div(cls="inner2"), Text("B"):
                pass

        assert len(outer.children) == 2
        assert outer.children[0].props.get("cls") == "inner1"
        assert outer.children[1].props.get("cls") == "inner2"
        assert len(outer.children[0].children) == 1
        # Text element has content attribute
        text_el = outer.children[0].children[0]
        assert hasattr(text_el, "content")
        assert text_el.content == "A"
