"""Test ConsoleRenderer can be imported from wtfui.tui."""


def test_console_renderer_import_from_tui():
    """ConsoleRenderer should be importable from wtfui.tui."""
    from wtfui.tui import ConsoleRenderer

    assert ConsoleRenderer is not None


def test_console_renderer_renders():
    """ConsoleRenderer from wtfui.tui should render."""
    from wtfui.core.protocol import RenderNode
    from wtfui.tui import ConsoleRenderer

    renderer = ConsoleRenderer(width=80, height=24)
    node = RenderNode(tag="div", element_id=1, props={}, children=[])
    renderer.render_node(node)
    output = renderer.flush()

    assert output is not None
