# tests/test_package_exports.py
"""Tests for package exports - clean public API."""


def test_core_exports():
    """Core classes are exported from flow package."""
    from flow import Computed, Effect, Element, Signal, component

    assert Element is not None
    assert Signal is not None
    assert Effect is not None
    assert Computed is not None
    assert component is not None


def test_ui_exports():
    """UI elements are exported from flow.ui."""
    from flow.ui import Button, Card, Div, HStack, Input, Text, VStack, Window

    assert Div is not None
    assert Text is not None
    assert Button is not None
    assert Input is not None
    assert VStack is not None
    assert HStack is not None
    assert Card is not None
    assert Window is not None


def test_renderer_exports():
    """Renderer classes are exported from flow.renderer."""
    from flow.renderer import DOMRenderer, HTMLRenderer, Renderer, RenderNode

    assert Renderer is not None
    assert RenderNode is not None
    assert HTMLRenderer is not None
    assert DOMRenderer is not None


def test_rpc_exports():
    """RPC utilities are exported from flow.rpc."""
    from flow.rpc import FlowJSONEncoder, RpcRegistry, rpc

    assert rpc is not None
    assert RpcRegistry is not None
    assert FlowJSONEncoder is not None


def test_server_exports():
    """Server utilities are exported from flow.server."""
    from flow.server import LiveSession, create_app, run_app

    assert LiveSession is not None
    assert create_app is not None
    assert run_app is not None


def test_injection_exports():
    """DI utilities are exported from flow.injection."""
    from flow.injection import clear_providers, get_provider, provide

    assert provide is not None
    assert get_provider is not None
    assert clear_providers is not None


def test_dev_exports():
    """Dev utilities are exported from flow.dev."""
    from flow.dev import split_server_client

    assert split_server_client is not None


def test_top_level_convenience():
    """Commonly used items exported at top level."""
    from flow import Effect, Element, Signal, component

    # These should all be importable from the top-level package
    assert callable(component)
    assert Effect is not None
    assert Signal is not None
    assert Element is not None
