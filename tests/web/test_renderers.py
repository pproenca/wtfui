"""Test renderers can be imported from wtfui.web."""


def test_html_renderer_import_from_web():
    """HTMLRenderer should be importable from wtfui.web."""
    from wtfui.web import HTMLRenderer

    assert HTMLRenderer is not None


def test_dom_renderer_import_from_web():
    """DOMRenderer should be importable from wtfui.web."""
    from wtfui.web import DOMRenderer

    assert DOMRenderer is not None


def test_html_renderer_renders():
    """HTMLRenderer from wtfui.web should render."""
    from wtfui.core.protocol import RenderNode
    from wtfui.web import HTMLRenderer

    renderer = HTMLRenderer()
    node = RenderNode(tag="div", element_id=1, props={}, children=[])
    html = renderer.render_node(node)

    assert "<div" in html
