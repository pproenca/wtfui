"""Tests for Element focusable property."""


def test_element_focusable_default_false():
    """Element should have focusable=False by default."""
    from wtfui.core.element import Element

    elem = Element()
    assert elem.focusable is False


def test_element_focusable_can_be_set():
    """Element should accept focusable=True."""
    from wtfui.core.element import Element

    elem = Element(focusable=True)
    assert elem.focusable is True


def test_input_element_focusable_true():
    """Input element should be focusable by default."""
    from wtfui.ui import Input

    inp = Input()
    assert inp.focusable is True
