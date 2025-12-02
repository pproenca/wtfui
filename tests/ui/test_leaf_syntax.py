"""Tests for leaf node syntax with UI elements."""

from flow.ui.elements import Button, Div, Input, Text, VStack


def test_text_auto_mounts():
    """Text element auto-mounts without with block."""
    with Div() as container:
        text = Text("Hello, World!")

    assert text in container.children
    assert text.content == "Hello, World!"


def test_input_auto_mounts():
    """Input element auto-mounts without with block."""
    with Div() as container:
        input_el = Input(placeholder="Enter name")

    assert input_el in container.children


def test_button_auto_mounts():
    """Button element auto-mounts without with block."""
    clicked = []

    with Div() as container:
        btn = Button("Click me", on_click=lambda: clicked.append(1))

    assert btn in container.children
    assert btn.label == "Click me"


def test_form_layout_with_leaf_syntax():
    """Complex form layout using leaf syntax."""
    with Div() as form:
        Text("Login Form")

        with VStack() as fields:
            Text("Username")
            Input(placeholder="Enter username")
            Text("Password")
            Input(placeholder="Enter password")

        Button("Submit")

    # Form has: Text, VStack, Button
    assert len(form.children) == 3
    assert isinstance(form.children[0], Text)
    assert isinstance(form.children[1], VStack)
    assert isinstance(form.children[2], Button)

    # VStack has: Text, Input, Text, Input
    assert len(fields.children) == 4


def test_nested_containers_with_leaf_nodes():
    """Deeply nested containers with auto-mounted leaves."""
    with Div() as root:  # noqa: SIM117 - Testing nested context managers
        with VStack() as outer:
            Text("Outer")
            with VStack() as inner:
                Text("Inner 1")
                Text("Inner 2")
            Text("After inner")

    assert len(root.children) == 1  # VStack
    assert len(outer.children) == 3  # Text, VStack, Text
    assert len(inner.children) == 2  # Text, Text
