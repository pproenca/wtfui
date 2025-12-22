"""Tests for complete public API exports."""


def test_core_exports():
    """Core classes are exported."""
    from wtfui import (
        Computed,
        Effect,
        Element,
        Signal,
        component,
        get_provider,
        provide,
        rpc,
    )

    assert all([Element, Signal, Effect, Computed, component, rpc, provide, get_provider])


def test_ui_exports():
    """UI elements are exported."""
    from wtfui.ui import Button, Card, Div, HStack, Input, Text, VStack, Window

    assert all([Div, VStack, HStack, Text, Button, Input, Card, Window])


def test_renderer_exports():
    """Renderers are exported."""
    from wtfui.core.protocol import Renderer, RenderNode
    from wtfui.tui.renderer import ConsoleRenderer
    from wtfui.web.renderer import DOMRenderer, HTMLRenderer

    assert all([Renderer, RenderNode, HTMLRenderer, DOMRenderer, ConsoleRenderer])


def test_server_exports():
    """Server utilities are exported."""
    from wtfui.web.server import LiveSession, create_app, run_app

    assert all([create_app, run_app, LiveSession])


def test_compiler_exports():
    """Compiler tools are exported."""
    from wtfui.web.compiler import (
        install_import_hook,
        transform_for_client,
        uninstall_import_hook,
    )

    assert all([transform_for_client, install_import_hook, uninstall_import_hook])


def test_runtime_exports():
    """Runtime utilities are exported."""
    from wtfui.core.registry import ElementRegistry
    from wtfui.core.router import HistoryState, Route, Router, handle_navigation_key
    from wtfui.tui.runtime import TUIRuntime, run_tui_app

    assert all(
        [
            ElementRegistry,
            HistoryState,
            Route,
            Router,
            TUIRuntime,
            handle_navigation_key,
            run_tui_app,
        ]
    )


def test_wasm_exports():
    """Wasm utilities are exported."""
    from wtfui.web.wasm import WtfUIApp, is_browser, is_server, mount

    assert all([WtfUIApp, mount, is_browser, is_server])


def test_build_exports():
    """Build utilities are exported."""
    from wtfui.web.build import (
        generate_client_bundle,
        generate_html_shell,
        generate_pyodide_loader,
    )

    assert all([generate_client_bundle, generate_html_shell, generate_pyodide_loader])


def test_cli_module_exports():
    """CLI submodules are importable after restructuring."""
    from wtfui.cli.builders import build_pyodide, build_wtfuibyte
    from wtfui.cli.vm import get_vm_inline

    assert all([get_vm_inline, build_wtfuibyte, build_pyodide])
