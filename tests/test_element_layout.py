# tests/test_element_layout.py
from flow.element import Element
from flow.layout.style import FlexDirection
from flow.layout.types import Dimension


class TestElementLayout:
    def test_element_has_layout_style(self):
        """Elements can have layout styles."""
        elem = Element(
            flex_direction="row",
            justify_content="center",
            width=100,
            height=50,
        )

        style = elem.get_layout_style()
        assert style.flex_direction == FlexDirection.ROW
        assert style.width == Dimension.points(100)

    def test_element_to_layout_node(self):
        """Elements can convert to LayoutNodes."""
        parent = Element(width=200, height=100, flex_direction="row")
        parent.__enter__()

        child1 = Element(flex_grow=1)
        child1.__enter__()
        child1.__exit__(None, None, None)

        child2 = Element(flex_grow=1)
        child2.__enter__()
        child2.__exit__(None, None, None)

        parent.__exit__(None, None, None)

        layout_node = parent.to_layout_node()

        assert len(layout_node.children) == 2
        assert layout_node.style.flex_direction == FlexDirection.ROW

    def test_element_default_layout_style(self):
        """Elements with no layout props get default FlexStyle."""
        elem = Element()
        style = elem.get_layout_style()

        assert style.flex_direction == FlexDirection.ROW
        assert style.flex_grow == 0.0

    def test_element_percent_dimension(self):
        """Elements can have percentage dimensions."""
        elem = Element(width="50%", height="100%")
        style = elem.get_layout_style()

        assert style.width == Dimension.percent(50)
        assert style.height == Dimension.percent(100)

    def test_element_layout_props_mixed_with_other_props(self):
        """Layout props work alongside other element props."""
        elem = Element(
            id="my-element",  # regular prop
            class_="container",  # regular prop
            flex_grow=1.0,  # layout prop
            width=100,  # layout prop
        )

        # Regular props still accessible
        assert elem.props["id"] == "my-element"
        assert elem.props["class_"] == "container"

        # Layout style reflects layout props
        style = elem.get_layout_style()
        assert style.flex_grow == 1.0
        assert style.width == Dimension.points(100)
