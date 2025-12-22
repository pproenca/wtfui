# tests/test_renderer_html.py
"""Tests for HTMLRenderer - HTML string rendering with XSS protection."""

from wtfui.core.protocol import RenderNode
from wtfui.web.renderer.html import HTMLRenderer


def test_html_escapes_quotes_in_attributes():
    """Quotes in attributes must be escaped to prevent XSS."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"title": 'He said "hello"', "data-test": "it's fine"},
        children=[],
    )

    html = renderer.render_node(node)

    # Double quotes should be escaped
    assert "&quot;" in html, f"Expected &quot; in: {html}"
    # Single quotes should be escaped
    assert "&#x27;" in html, f"Expected &#x27; in: {html}"


def test_html_escapes_angle_brackets_in_text():
    """Angle brackets in text content must be escaped to prevent XSS."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={},
        children=[],
        text_content="<script>alert('xss')</script>",
    )

    html = renderer.render_node(node)

    # Script tag should be escaped
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_escapes_ampersand_in_text():
    """Ampersands in text content must be escaped."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={},
        children=[],
        text_content="Tom & Jerry",
    )

    html = renderer.render_node(node)

    assert "&amp;" in html
    assert "Tom &amp; Jerry" in html


# === Regression tests for Style-to-CSS conversion ===


def test_style_object_converts_to_css_not_repr():
    """Style objects must be converted to CSS, not Python repr strings.

    Regression test: Previously Style objects were rendered as their Python
    repr string (e.g., "Style(color=None, bg='white', ...)") instead of
    being converted to actual CSS properties.
    """
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(bg="white", color="slate-900", font_weight="bold")
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    # Must NOT contain Python repr
    assert "Style(" not in html, f"Style repr found in HTML: {html}"
    assert "_wtfui_style" not in html, f"_wtfui_style key found in HTML: {html}"

    # Must contain actual CSS
    assert "background-color:" in html, f"CSS background-color not found: {html}"
    assert "font-weight: bold" in html, f"CSS font-weight not found: {html}"


def test_style_colors_convert_to_hex():
    """Tailwind-style color names must convert to hex CSS values."""
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(bg="slate-900", color="blue-600")
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    # Colors should be converted to hex
    assert "#0f172a" in html, f"slate-900 hex not found: {html}"
    assert "#2563eb" in html, f"blue-600 hex not found: {html}"


def test_style_font_sizes_convert_to_rem():
    """Font size keywords must convert to rem values."""
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(font_size="xl")
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    assert "font-size: 1.25rem" in html, f"Font size rem value not found: {html}"


def test_style_spacing_converts_to_px():
    """Spacing values must convert to px units."""
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(p=16, mt=8, px=12)
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    assert "padding: 16px" in html, f"Padding px not found: {html}"
    assert "margin-top: 8px" in html, f"Margin-top px not found: {html}"


def test_style_border_converts_to_css():
    """Border properties must convert to CSS border declarations."""
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(border=True, border_color="slate-200", rounded="lg")
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    assert "border:" in html, f"Border declaration not found: {html}"
    assert "border-radius:" in html, f"Border-radius not found: {html}"


def test_style_shadow_converts_to_box_shadow():
    """Shadow property must convert to box-shadow CSS."""
    from wtfui.core.style import Style

    renderer = HTMLRenderer()
    style = Style(shadow="md")
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={"style": {"_wtfui_style": style}},
        children=[],
    )

    html = renderer.render_node(node)

    assert "box-shadow:" in html, f"Box-shadow not found: {html}"


def test_layout_props_convert_to_css_not_html_attrs():
    """Layout props like flex_direction must become CSS, not HTML attributes.

    Regression test: Previously layout props were rendered as HTML attributes
    (e.g., flex_direction="column") instead of CSS style properties.
    """
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={
            "flex_direction": "column",
            "justify_content": "space-between",
            "align_items": "center",
            "gap": 16,
        },
        children=[],
    )

    html = renderer.render_node(node)

    # Must NOT have layout props as HTML attributes
    assert 'flex_direction="' not in html, f"flex_direction as attr: {html}"
    assert 'justify_content="' not in html, f"justify_content as attr: {html}"

    # Must have CSS in style attribute
    assert "display: flex" in html, f"display: flex not found: {html}"
    assert "flex-direction: column" in html, f"flex-direction CSS not found: {html}"
    assert "justify-content: space-between" in html, f"justify-content CSS not found: {html}"
    assert "align-items: center" in html, f"align-items CSS not found: {html}"
    assert "gap: 16px" in html, f"gap CSS not found: {html}"


def test_layout_size_props_convert_to_css_with_units():
    """Width, height, padding props must convert to CSS with px units."""
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Div",
        element_id=1,
        props={
            "width": 200,
            "height": "100vh",
            "padding": 24,
        },
        children=[],
    )

    html = renderer.render_node(node)

    # Numeric values get px units
    assert "width: 200px" in html, f"width CSS not found: {html}"
    assert "padding: 24px" in html, f"padding CSS not found: {html}"
    # String values preserved as-is
    assert "height: 100vh" in html, f"height CSS not found: {html}"


def test_box_defaults_to_flex_column():
    """Box components should default to flex column layout.

    Regression test: Without this, Text children inside Box appear inline
    instead of stacking vertically.
    """
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Box",
        element_id=1,
        props={},
        children=[],
    )

    html = renderer.render_node(node)

    assert "display: flex" in html, f"display: flex not found: {html}"
    assert "flex-direction: column" in html, f"flex-direction: column not found: {html}"


def test_text_renders_as_inline_span():
    """Text elements should render as span (inline).

    To stack Text elements vertically, wrap them in Flex(direction='column').
    """
    renderer = HTMLRenderer()
    node = RenderNode(
        tag="Text",
        element_id=1,
        props={},
        children=[],
        text_content="Hello",
    )

    html = renderer.render_node(node)

    # Should be a span for inline semantics
    assert html.startswith("<span"), f"Expected span tag: {html}"
