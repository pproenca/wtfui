"""Tests for run_tui console runtime helper."""

import pytest


class TestRunTuiImport:
    """Test that run_tui can be imported."""

    def test_run_tui_importable(self) -> None:
        """run_tui should be importable from wtfui.tui.renderer."""
        from wtfui.tui.renderer import run_tui

        assert callable(run_tui)

    def test_run_tui_accepts_component(self) -> None:
        """run_tui signature accepts a component function."""
        import inspect

        from wtfui.tui.renderer import run_tui

        sig = inspect.signature(run_tui)
        params = list(sig.parameters.keys())
        assert "component" in params or "app" in params


class TestMouseIntegration:
    """Test mouse event integration into runtime loop."""

    def test_run_tui_accepts_mouse_parameter(self):
        """run_tui should accept mouse parameter and pass it through."""
        import inspect

        from wtfui.tui.renderer.runtime import run_tui

        sig = inspect.signature(run_tui)
        params = list(sig.parameters.keys())

        # Verify mouse parameter exists
        assert "mouse" in params

        # Verify default is True
        assert sig.parameters["mouse"].default is True


class TestLayoutCaching:
    """Test that layout nodes are cached and reused via LayoutAdapter."""

    @pytest.mark.asyncio
    async def test_layout_cache_works_within_element_lifetime(self):
        """Verify layout node is cached when using LayoutAdapter cache dict."""
        from wtfui.core.element import Element
        from wtfui.tui.adapter import LayoutAdapter
        from wtfui.tui.layout.node import LayoutNode

        class TestElement(Element):
            pass

        elem = TestElement()
        adapter = LayoutAdapter()
        cache: dict[int, LayoutNode] = {}

        # First call creates the layout node
        node1 = adapter.to_layout_node(elem, cache=cache)
        assert isinstance(node1, LayoutNode)

        # Second call with same cache returns the cached node
        node2 = adapter.to_layout_node(elem, cache=cache)
        assert node1 is node2, "to_layout_node with cache should return cached instance"

        # Using a new cache creates a new node
        new_cache: dict[int, LayoutNode] = {}
        node3 = adapter.to_layout_node(elem, cache=new_cache)
        assert node1 is not node3, "With fresh cache, new node should be created"


class TestRunTuiUsesTUIRuntime:
    """Tests that run_tui delegates to TUIRuntime."""

    def test_run_tui_creates_tui_runtime(self, monkeypatch):
        """run_tui should instantiate TUIRuntime with correct parameters."""
        from unittest.mock import MagicMock, patch

        mock_runtime_class = MagicMock()
        mock_runtime_instance = MagicMock()
        mock_runtime_class.return_value = mock_runtime_instance

        with patch("wtfui.tui.renderer.runtime.TUIRuntime", mock_runtime_class):
            from wtfui.tui.renderer.runtime import run_tui

            def app():
                pass

            def handler(key: str) -> None:
                pass

            run_tui(app, fps=30, mouse=False, on_key=handler)

            mock_runtime_class.assert_called_once_with(
                app, fps=30, mouse=False, on_key=handler, inline=False
            )
            mock_runtime_instance.start.assert_called_once()
