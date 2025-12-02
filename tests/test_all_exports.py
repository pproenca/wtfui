"""Tests for complete public API exports."""


def test_core_exports():
    """Core classes are exported."""
    from flow import (
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
    from flow.ui import Button, Card, Div, HStack, Input, Text, VStack, Window

    assert all([Div, VStack, HStack, Text, Button, Input, Card, Window])


def test_renderer_exports():
    """Renderers are exported."""
    from flow.renderer import DOMRenderer, HTMLRenderer, Renderer, RenderNode

    assert all([Renderer, RenderNode, HTMLRenderer, DOMRenderer])


def test_server_exports():
    """Server utilities are exported."""
    from flow.server import LiveSession, create_app, run_app

    assert all([create_app, run_app, LiveSession])


def test_compiler_exports():
    """Compiler tools are exported."""
    from flow.compiler import (
        install_import_hook,
        transform_for_client,
        uninstall_import_hook,
    )

    assert all([transform_for_client, install_import_hook, uninstall_import_hook])


def test_runtime_exports():
    """Runtime utilities are exported."""
    from flow.runtime import ElementRegistry

    assert ElementRegistry is not None


def test_wasm_exports():
    """Wasm utilities are exported."""
    from flow.wasm import FlowApp, is_browser, is_server, mount

    assert all([FlowApp, mount, is_browser, is_server])


def test_build_exports():
    """Build utilities are exported."""
    from flow.build import (
        generate_client_bundle,
        generate_html_shell,
        generate_pyodide_loader,
    )

    assert all([generate_client_bundle, generate_html_shell, generate_pyodide_loader])
