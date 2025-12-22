# tests/element/test_layout_caching.py

"""Tests for LayoutAdapter caching functionality."""

from wtfui.core.element import Element
from wtfui.tui.adapter import LayoutAdapter


class MockElement(Element):
    """Concrete Element for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def test_to_layout_node_returns_cached_instance():
    """Calling to_layout_node with same cache returns the same LayoutNode."""
    elem = MockElement()
    adapter = LayoutAdapter()
    cache: dict[int, object] = {}

    node1 = adapter.to_layout_node(elem, cache=cache)
    node2 = adapter.to_layout_node(elem, cache=cache)

    assert node1 is node2, "to_layout_node with cache should return cached instance"


def test_to_layout_node_children_share_cache():
    """Child elements also return cached layout nodes when using same cache."""
    parent = MockElement()

    with parent:
        child = MockElement()

    adapter = LayoutAdapter()
    cache: dict[int, object] = {}

    # First call creates cache
    parent_node = adapter.to_layout_node(parent, cache=cache)
    child_node = adapter.to_layout_node(child, cache=cache)

    # Verify child is in parent's children
    assert len(parent_node.children) == 1
    assert parent_node.children[0] is child_node


def test_new_cache_creates_new_nodes():
    """Using a fresh cache creates new layout nodes."""
    elem = MockElement()
    adapter = LayoutAdapter()

    cache1: dict[int, object] = {}
    cache2: dict[int, object] = {}

    node1 = adapter.to_layout_node(elem, cache=cache1)
    node2 = adapter.to_layout_node(elem, cache=cache2)

    assert node1 is not node2, "Fresh cache should create new node"


def test_no_cache_creates_new_nodes_each_time():
    """Without cache, each call creates a new LayoutNode."""
    elem = MockElement()
    adapter = LayoutAdapter()

    node1 = adapter.to_layout_node(elem, cache=None)
    node2 = adapter.to_layout_node(elem, cache=None)

    assert node1 is not node2, "Without cache, new node should be created each time"


def test_adding_child_requires_fresh_cache():
    """When children change, a fresh cache should be used for new layout."""
    parent = MockElement()
    adapter = LayoutAdapter()

    cache1: dict[int, object] = {}
    parent_node1 = adapter.to_layout_node(parent, cache=cache1)

    with parent:
        _child = MockElement()

    # Use fresh cache after children changed
    cache2: dict[int, object] = {}
    parent_node2 = adapter.to_layout_node(parent, cache=cache2)

    # Parent should have new node since we used fresh cache
    assert parent_node1 is not parent_node2
    # New node should have the child
    assert len(parent_node2.children) == 1


def test_style_change_detected_with_fresh_cache():
    """Style changes are reflected when using a fresh cache."""
    elem = MockElement(width=100)
    adapter = LayoutAdapter()

    cache1: dict[int, object] = {}
    node1 = adapter.to_layout_node(elem, cache=cache1)
    width1 = node1.style.width

    # Change style
    elem.set_style(width=200)

    # Use fresh cache to get updated style
    cache2: dict[int, object] = {}
    node2 = adapter.to_layout_node(elem, cache=cache2)
    width2 = node2.style.width

    assert node1 is not node2, "Fresh cache should create new node"
    assert width1 != width2, "Style change should be reflected in new node"
