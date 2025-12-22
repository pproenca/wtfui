# tests/renderer/test_protocol.py
"""Tests for the Renderer Protocol."""

from wtfui.core.protocol import RenderNode
from wtfui.tui.layout.node import LayoutResult


def test_render_node_accepts_layout_result():
    """Verify RenderNode can store LayoutResult directly."""
    layout = LayoutResult(x=10.0, y=20.0, width=100.0, height=50.0)

    node = RenderNode(
        tag="div",
        element_id=123,
        props={},
        layout=layout,
    )

    assert node.layout is not None
    assert node.layout.x == 10.0
    assert node.layout.y == 20.0
    assert node.layout.width == 100.0
    assert node.layout.height == 50.0
