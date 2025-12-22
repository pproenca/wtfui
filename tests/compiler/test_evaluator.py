"""Tests for static style evaluator.

Verifies that the style evaluator correctly extracts static styles
and returns DYNAMIC_STYLE sentinel for dynamic styles.
"""

import ast

from wtfui.web.compiler.evaluator import (
    DYNAMIC_STYLE,
    DynamicStyleSentinel,
    get_style_repr,
    is_static_style,
    safe_eval_style,
)


def parse_expr(code: str) -> ast.expr:
    """Parse expression code to AST node."""
    return ast.parse(code, mode="eval").body


def test_dynamic_style_sentinel():
    """DynamicStyleSentinel is a singleton marker."""
    assert isinstance(DYNAMIC_STYLE, DynamicStyleSentinel)
    assert repr(DYNAMIC_STYLE) == "DYNAMIC_STYLE"


def test_static_style_dict():
    """Dict literal styles are statically extracted."""
    node = parse_expr("{'background': 'blue', 'color': 'white'}")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert result["background"] == "blue"
    assert result["color"] == "white"


def test_static_style_with_numbers():
    """Numeric values are extracted."""
    node = parse_expr("{'padding': 10, 'margin': 20}")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert result["padding"] == 10
    assert result["margin"] == 20


def test_static_style_css_string():
    """CSS string styles are parsed."""
    node = parse_expr("'background: red; padding: 5px'")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert result["background"] == "red"
    assert result["padding"] == "5px"


def test_theme_color_reference():
    """Theme color references are resolved."""
    node = parse_expr("Colors.Blue._500")
    result = safe_eval_style(ast.Dict(keys=[ast.Constant("bg")], values=[node]))

    # Should not raise - theme reference should be resolved
    assert isinstance(result, dict)
    assert result["bg"] == "#3b82f6"


def test_dynamic_function_call():
    """Function calls return DYNAMIC_STYLE."""
    node = parse_expr("get_style()")
    result = safe_eval_style(node)

    assert result is DYNAMIC_STYLE


def test_dynamic_variable_reference():
    """Variable references return DYNAMIC_STYLE."""
    node = parse_expr("{'bg': my_color}")
    result = safe_eval_style(node)

    assert result is DYNAMIC_STYLE


def test_dynamic_fstring():
    """f-strings return DYNAMIC_STYLE."""
    # Create a proper FormattedValue node with all required arguments
    formatted = ast.FormattedValue(
        value=ast.Name(id="color", ctx=ast.Load()),
        conversion=-1,  # No conversion
        format_spec=None,
    )
    node = ast.JoinedStr(values=[ast.Constant("background: "), formatted])
    result = safe_eval_style(ast.Dict(keys=[ast.Constant("style")], values=[node]))

    assert result is DYNAMIC_STYLE


def test_is_static_style_true():
    """is_static_style returns True for static styles."""
    node = parse_expr("{'background': 'blue'}")
    assert is_static_style(node) is True


def test_is_static_style_false():
    """is_static_style returns False for dynamic styles."""
    node = parse_expr("get_style()")
    assert is_static_style(node) is False


def test_get_style_repr():
    """get_style_repr returns string representation."""
    node = parse_expr("{'background': 'blue'}")
    repr_str = get_style_repr(node)

    assert "background" in repr_str
    assert "blue" in repr_str


def test_negative_numbers():
    """Negative numbers are handled."""
    node = parse_expr("{'margin': -10}")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert result["margin"] == -10


def test_unknown_theme_reference():
    """Unknown theme references return DYNAMIC_STYLE."""
    node = parse_expr("Colors.Unknown._999")
    result = safe_eval_style(ast.Dict(keys=[ast.Constant("bg")], values=[node]))

    assert result is DYNAMIC_STYLE


def test_empty_css_string():
    """Empty CSS string returns empty dict."""
    node = parse_expr("''")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert len(result) == 0


def test_multiple_style_properties():
    """Multiple style properties are all extracted."""
    node = parse_expr("{'bg': 'red', 'p': 4, 'm': 2, 'border': '1px solid'}")
    result = safe_eval_style(node)

    assert isinstance(result, dict)
    assert len(result) == 4
    assert result["bg"] == "red"
    assert result["p"] == 4
    assert result["m"] == 2
    assert result["border"] == "1px solid"


def test_theme_slate_colors():
    """Slate color palette is available."""
    node = parse_expr("Colors.Slate._800")
    result = safe_eval_style(ast.Dict(keys=[ast.Constant("bg")], values=[node]))

    assert isinstance(result, dict)
    assert result["bg"] == "#1e293b"


def test_white_color():
    """Base white color is available."""
    node = parse_expr("Colors.White")
    result = safe_eval_style(ast.Dict(keys=[ast.Constant("bg")], values=[node]))

    assert isinstance(result, dict)
    assert result["bg"] == "#ffffff"
