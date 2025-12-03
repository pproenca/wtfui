"""Tests for atomic CSS generator.

Verifies that the CSS generator correctly:
- Generates unique class names
- Deduplicates identical styles
- Expands property aliases
- Converts numeric values to CSS units
"""

from flow.compiler.css import CSSGenerator


def test_css_generator_creation():
    """CSSGenerator can be instantiated."""
    css = CSSGenerator()
    assert len(css) == 0


def test_register_simple_style():
    """register returns class name for simple style."""
    css = CSSGenerator()
    class_name = css.register({"background": "blue"})

    assert class_name.startswith("fl-")
    assert len(class_name) == 9  # fl- + 6 chars


def test_deduplication():
    """Identical styles return the same class name."""
    css = CSSGenerator()
    cls1 = css.register({"background": "blue", "padding": "4px"})
    cls2 = css.register({"background": "blue", "padding": "4px"})
    cls3 = css.register({"padding": "4px", "background": "blue"})  # Different order

    assert cls1 == cls2
    assert cls1 == cls3
    assert len(css) == 1


def test_different_styles_different_classes():
    """Different styles get different class names."""
    css = CSSGenerator()
    cls1 = css.register({"background": "blue"})
    cls2 = css.register({"background": "red"})

    assert cls1 != cls2
    assert len(css) == 2


def test_property_alias_expansion():
    """Property aliases are expanded to CSS properties."""
    css = CSSGenerator()
    css.register({"bg": "#3b82f6", "p": 4})

    output = css.get_output()
    assert "background-color:#3b82f6" in output
    assert "padding:4px" in output


def test_numeric_value_conversion():
    """Numeric values are converted to px units."""
    css = CSSGenerator()
    css.register({"width": 100, "height": 50, "margin": 10})

    output = css.get_output()
    assert "width:100px" in output
    assert "height:50px" in output
    assert "margin:10px" in output


def test_string_values_unchanged():
    """String values are used as-is."""
    css = CSSGenerator()
    css.register({"display": "flex", "justify": "center"})

    output = css.get_output()
    assert "display:flex" in output
    assert "justify-content:center" in output


def test_get_output_minified():
    """get_output returns minified CSS by default."""
    css = CSSGenerator()
    css.register({"background": "blue", "color": "white"})

    output = css.get_output()
    # No newlines, no spaces in minified output
    assert "\n" not in output
    assert "{ " not in output


def test_get_output_formatted():
    """get_output(minified=False) returns formatted CSS."""
    css = CSSGenerator()
    css.register({"background": "blue"})

    output = css.get_output(minified=False)
    assert "\n" in output


def test_empty_output():
    """get_output returns empty string for no styles."""
    css = CSSGenerator()
    assert css.get_output() == ""


def test_clear():
    """clear removes all registered styles."""
    css = CSSGenerator()
    css.register({"background": "blue"})
    assert len(css) == 1

    css.clear()
    assert len(css) == 0
    assert css.get_output() == ""


def test_custom_prefix():
    """Custom prefix is used in class names."""
    css = CSSGenerator(prefix="app")
    class_name = css.register({"color": "red"})

    assert class_name.startswith("app-")


def test_spacing_aliases():
    """Spacing property aliases work correctly."""
    css = CSSGenerator()
    css.register(
        {
            "pt": 10,
            "pr": 20,
            "pb": 10,
            "pl": 20,
            "mt": 5,
            "mb": 5,
        }
    )

    output = css.get_output()
    assert "padding-top:10px" in output
    assert "padding-right:20px" in output
    assert "margin-top:5px" in output


def test_layout_aliases():
    """Layout property aliases work correctly."""
    css = CSSGenerator()
    css.register(
        {
            "flex": 1,
            "flex-direction": "column",
            "justify": "space-between",
            "items": "center",
            "gap": 8,
        }
    )

    output = css.get_output()
    assert "flex:1" in output
    assert "flex-direction:column" in output
    assert "justify-content:space-between" in output
    assert "align-items:center" in output
    assert "gap:8px" in output


def test_multiple_classes_output():
    """Multiple registered classes appear in output."""
    css = CSSGenerator()
    css.register({"background": "blue"})
    css.register({"background": "red"})
    css.register({"background": "green"})

    output = css.get_output()
    # All three classes should be present
    assert output.count(".fl-") == 3


def test_hash_determinism():
    """Same styles produce same hash across instances."""
    css1 = CSSGenerator()
    css2 = CSSGenerator()

    cls1 = css1.register({"background": "#3b82f6", "padding": "4px"})
    cls2 = css2.register({"background": "#3b82f6", "padding": "4px"})

    assert cls1 == cls2
