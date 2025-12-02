# tests/test_layout_algorithm.py
from flow.layout.algorithm import AvailableSpace, SizingMode


class TestAvailableSpace:
    def test_definite_space(self):
        space = AvailableSpace.definite(100)
        assert space.is_definite()
        assert space.value == 100

    def test_min_content(self):
        space = AvailableSpace.min_content()
        assert space.is_min_content()

    def test_max_content(self):
        space = AvailableSpace.max_content()
        assert space.is_max_content()

    def test_resolve_definite(self):
        space = AvailableSpace.definite(200)
        assert space.resolve() == 200

    def test_resolve_min_content(self):
        space = AvailableSpace.min_content()
        assert space.resolve() == 0

    def test_resolve_max_content(self):
        space = AvailableSpace.max_content()
        assert space.resolve() == float("inf")


class TestSizingMode:
    def test_sizing_modes(self):
        assert SizingMode.CONTENT_BOX.is_content_box()
        assert SizingMode.BORDER_BOX.is_border_box()
