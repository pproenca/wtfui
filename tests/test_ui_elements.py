# tests/test_ui_elements.py
"""Tests for UI Elements - the building blocks of Flow interfaces."""

from flow.ui import Button, Div, HStack, Input, Text, VStack


def test_div_element():
    """Div creates a div element."""
    div = Div(cls="container")
    assert div.tag == "Div"
    assert div.props["cls"] == "container"


def test_text_element():
    """Text creates text content."""
    text = Text("Hello, World!")
    assert text.tag == "Text"
    assert text.content == "Hello, World!"


def test_button_element():
    """Button creates a button with click handler."""
    clicked: list[bool] = []
    btn = Button("Click me", on_click=lambda: clicked.append(True))
    assert btn.tag == "Button"
    assert btn.label == "Click me"
    assert "on_click" in btn.props


def test_input_element():
    """Input creates an input field."""
    from flow import Signal

    value = Signal("")
    inp = Input(bind=value, placeholder="Enter text")
    assert inp.tag == "Input"
    assert inp.props["placeholder"] == "Enter text"


def test_vstack_layout():
    """VStack stacks children vertically."""
    with VStack(gap=4) as stack:
        with Div():
            pass
        with Div():
            pass

    assert stack.tag == "VStack"
    assert len(stack.children) == 2
    assert stack.props["gap"] == 4


def test_hstack_layout():
    """HStack stacks children horizontally."""
    with HStack(gap=2) as stack:
        with Text("A"):
            pass
        with Text("B"):
            pass

    assert stack.tag == "HStack"
    assert len(stack.children) == 2


def test_props_support_future_style_architecture():
    """Props architecture supports future Style objects (V2 preparation)."""
    # V1: String-based classes
    div1 = Div(cls="container p-4")
    assert div1.props["cls"] == "container p-4"

    # V2-ready: Props can hold any value (Style objects in future)
    div2 = Div(padding=4, margin=2)  # Keyword-argument styling
    assert div2.props["padding"] == 4
    assert div2.props["margin"] == 2

    # The architecture allows both patterns to coexist
    div3 = Div(cls="container", padding=4)
    assert "cls" in div3.props
    assert "padding" in div3.props
