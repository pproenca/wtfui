# tests/test_element.py
"""Tests for Element base class - the foundation of all UI nodes."""

from flow.context import get_current_parent
from flow.element import Element


def test_element_has_tag_from_class_name():
    """Element tag defaults to class name."""
    el = Element()
    assert el.tag == "Element"


def test_element_stores_props():
    """Element stores arbitrary props."""
    el = Element(cls="container", id="main")
    assert el.props == {"cls": "container", "id": "main"}


def test_element_starts_with_no_children():
    """Element has empty children list."""
    el = Element()
    assert el.children == []


def test_element_context_manager_sets_parent():
    """Entering element sets it as current parent."""
    el = Element()
    assert get_current_parent() is None
    with el:
        assert get_current_parent() is el
    assert get_current_parent() is None


def test_element_nesting_builds_tree():
    """Nested context managers build parent-child relationships."""
    parent = Element()

    with parent:
        child = Element()  # Created INSIDE parent context

    assert child in parent.children
    assert child.parent is parent


def test_multiple_children():
    """Multiple children can be added to a parent."""
    parent = Element()

    with parent:
        child1 = Element()
        child2 = Element()

    assert parent.children == [child1, child2]


def test_element_auto_mounts_to_current_parent():
    """Element created inside a with block auto-attaches to parent."""
    parent = Element()

    with parent:
        child = Element()  # No 'with' block needed

    assert child in parent.children
    assert child.parent is parent


def test_element_detached_when_no_parent():
    """Element created outside any with block is detached."""
    el = Element()

    assert el.parent is None
    assert el.children == []


def test_auto_mount_multiple_children():
    """Multiple elements auto-mount in creation order."""
    parent = Element()

    with parent:
        child1 = Element()
        child2 = Element()
        child3 = Element()

    assert parent.children == [child1, child2, child3]
    assert all(c.parent is parent for c in parent.children)


def test_auto_mount_mixed_with_context_manager():
    """Auto-mount works alongside traditional with blocks."""
    parent = Element()

    with parent:
        leaf1 = Element()  # Auto-mounted
        with Element() as container:  # Traditional with block
            nested_leaf = Element()  # Auto-mounted to container
        leaf2 = Element()  # Auto-mounted to parent

    assert parent.children == [leaf1, container, leaf2]
    assert container.children == [nested_leaf]
    assert nested_leaf.parent is container
