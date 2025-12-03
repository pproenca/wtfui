"""Tests for DOM styling compilation.

Verifies that the FlowByte compiler correctly generates opcodes for
static styles, dynamic styles, and the Dynamic Style Fallback mechanism.
"""

from flow.cli import _get_vm_inline
from flow.compiler.flowbyte import compile_to_flowbyte
from flow.compiler.opcodes import OpCode


def test_static_style_dict_compilation():
    """Static style dict compiles to DOM_STYLE_STATIC opcodes."""
    source = """
with Div(style={"background": "blue", "color": "white"}):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Verify DOM_STYLE_STATIC opcode is present
    assert bytes([OpCode.DOM_STYLE_STATIC]) in binary


def test_static_style_string_compilation():
    """Static style string compiles to DOM_STYLE_STATIC opcodes."""
    source = """
with Div(style="background: red; padding: 10px"):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Verify DOM_STYLE_STATIC opcode is present
    assert bytes([OpCode.DOM_STYLE_STATIC]) in binary


def test_class_attribute_compilation():
    """class_ attribute compiles to DOM_ATTR_CLASS opcode."""
    source = """
with Div(class_="container mx-auto"):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Verify DOM_ATTR_CLASS opcode is present
    assert bytes([OpCode.DOM_ATTR_CLASS]) in binary


def test_cls_attribute_compilation():
    """cls attribute (alias for class_) compiles to DOM_ATTR_CLASS opcode."""
    source = """
with Div(cls="flex items-center"):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Verify DOM_ATTR_CLASS opcode is present
    assert bytes([OpCode.DOM_ATTR_CLASS]) in binary


def test_id_attribute_compilation():
    """id attribute compiles to DOM_ATTR opcode."""
    source = """
with Div(id="main-content"):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Verify DOM_ATTR opcode is present
    assert bytes([OpCode.DOM_ATTR]) in binary


def test_style_strings_in_pool():
    """Style properties and values are added to string pool."""
    source = """
with Div(style={"background-color": "navy"}):
    pass
"""
    binary = compile_to_flowbyte(source)

    # String "background-color" and "navy" should be in the binary
    assert b"background-color" in binary
    assert b"navy" in binary


def test_multiple_styles_compilation():
    """Multiple style properties compile to multiple DOM_STYLE_STATIC opcodes."""
    source = """
with Div(style={"margin": "10px", "padding": "20px", "border": "1px solid"}):
    pass
"""
    binary = compile_to_flowbyte(source)

    # Count DOM_STYLE_STATIC opcodes (should be 3)
    style_count = binary.count(bytes([OpCode.DOM_STYLE_STATIC]))
    assert style_count == 3


def test_element_without_style():
    """Elements without style don't emit style opcodes."""
    source = """
with Div():
    pass
"""
    binary = compile_to_flowbyte(source)

    # No style opcodes should be present
    assert bytes([OpCode.DOM_STYLE_STATIC]) not in binary
    assert bytes([OpCode.DOM_STYLE_DYN]) not in binary


def test_vm_has_style_handlers():
    """VM includes style opcode handlers."""
    js = _get_vm_inline()

    # Check for style opcodes
    assert "case 0x66:" in js  # DOM_STYLE_STATIC
    assert "case 0x67:" in js  # DOM_STYLE_DYN
    assert "case 0x68:" in js  # DOM_ATTR
    assert "case 0x69:" in js  # DOM_BIND_ATTR


def test_vm_converts_kebab_to_camel():
    """VM converts kebab-case CSS properties to camelCase."""
    js = _get_vm_inline()

    # Check for kebab-to-camel conversion
    assert "replace(/-([a-z])/g" in js


def test_vm_handles_css_text():
    """VM handles cssText for dynamic styles."""
    js = _get_vm_inline()

    assert "cssText" in js


def test_opcode_values():
    """Style opcodes have correct values."""
    assert OpCode.DOM_STYLE_STATIC.value == 0x66
    assert OpCode.DOM_STYLE_DYN.value == 0x67
    assert OpCode.DOM_ATTR.value == 0x68
    assert OpCode.DOM_BIND_ATTR.value == 0x69
