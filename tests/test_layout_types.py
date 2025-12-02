# tests/test_layout_types.py
from flow.layout.types import Border, Dimension, Edges, Rect, Size, Spacing


class TestDimension:
    def test_dimension_auto(self):
        dim = Dimension.auto()
        assert dim.is_auto()
        assert not dim.is_defined()

    def test_dimension_points(self):
        dim = Dimension.points(100)
        assert dim.value == 100
        assert dim.unit == "px"
        assert dim.is_defined()

    def test_dimension_percent(self):
        dim = Dimension.percent(50)
        assert dim.value == 50
        assert dim.unit == "%"

    def test_dimension_resolve_percent(self):
        dim = Dimension.percent(50)
        resolved = dim.resolve(200)  # 50% of 200 = 100
        assert resolved == 100


class TestSize:
    def test_size_creation(self):
        size = Size(width=100, height=50)
        assert size.width == 100
        assert size.height == 50

    def test_size_zero(self):
        size = Size.zero()
        assert size.width == 0
        assert size.height == 0


class TestRect:
    def test_rect_from_position_and_size(self):
        rect = Rect(x=10, y=20, width=100, height=50)
        assert rect.left == 10
        assert rect.top == 20
        assert rect.right == 110
        assert rect.bottom == 70


class TestFloatingPointPrecision:
    """Council Directive: Floating-point precision utilities."""

    def test_layout_epsilon_constant(self):
        from flow.layout.types import LAYOUT_EPSILON

        assert LAYOUT_EPSILON == 0.001

    def test_approx_equal_within_epsilon(self):
        from flow.layout.types import approx_equal

        assert approx_equal(1.0, 1.0009)
        assert approx_equal(0.3, 0.30000000004)
        assert not approx_equal(1.0, 1.002)

    def test_approx_equal_custom_epsilon(self):
        from flow.layout.types import approx_equal

        assert approx_equal(1.0, 1.05, epsilon=0.1)
        assert not approx_equal(1.0, 1.05, epsilon=0.01)

    def test_snap_to_pixel_default(self):
        from flow.layout.types import snap_to_pixel

        assert snap_to_pixel(10.4) == 10.0
        assert snap_to_pixel(10.6) == 11.0
        assert snap_to_pixel(10.5) == 10.0  # round half to even

    def test_snap_to_pixel_with_scale(self):
        from flow.layout.types import snap_to_pixel

        # Scale 2 = half-pixel grid (0, 0.5, 1.0, 1.5, ...)
        assert snap_to_pixel(10.3, scale=2) == 10.5
        assert snap_to_pixel(10.1, scale=2) == 10.0


class TestEdges:
    def test_edges_all(self):
        edges = Edges.all(10)
        assert edges.top == 10
        assert edges.right == 10
        assert edges.bottom == 10
        assert edges.left == 10

    def test_edges_symmetric(self):
        edges = Edges.symmetric(horizontal=20, vertical=10)
        assert edges.top == 10
        assert edges.bottom == 10
        assert edges.left == 20
        assert edges.right == 20

    def test_edges_horizontal_sum(self):
        edges = Edges(top=5, right=10, bottom=15, left=20)
        assert edges.horizontal == 30  # left + right
        assert edges.vertical == 20  # top + bottom


class TestSpacing:
    def test_spacing_resolve(self):
        spacing = Spacing(
            top=Dimension.points(10),
            right=Dimension.percent(10),
            bottom=Dimension.points(10),
            left=Dimension.auto(),
        )
        resolved = spacing.resolve(width=200, height=100)
        assert resolved.top == 10
        assert resolved.right == 20  # 10% of 200
        assert resolved.bottom == 10
        assert resolved.left == 0  # auto resolves to 0 for spacing


class TestBorder:
    def test_border_creation(self):
        border = Border(top=1, right=2, bottom=3, left=4)
        assert border.top == 1
        assert border.right == 2
        assert border.bottom == 3
        assert border.left == 4

    def test_border_defaults(self):
        border = Border()
        assert border.top == 0
        assert border.right == 0
        assert border.bottom == 0
        assert border.left == 0

    def test_border_all(self):
        border = Border.all(5)
        assert border.top == 5
        assert border.right == 5
        assert border.bottom == 5
        assert border.left == 5

    def test_border_zero(self):
        border = Border.zero()
        assert border.top == 0
        assert border.right == 0
        assert border.bottom == 0
        assert border.left == 0

    def test_border_horizontal_property(self):
        border = Border(top=1, right=2, bottom=3, left=4)
        assert border.horizontal == 6  # left + right = 4 + 2

    def test_border_vertical_property(self):
        border = Border(top=1, right=2, bottom=3, left=4)
        assert border.vertical == 4  # top + bottom = 1 + 3

    def test_border_resolve(self):
        border = Border(top=1, right=2, bottom=3, left=4)
        edges = border.resolve()
        assert isinstance(edges, Edges)
        assert edges.top == 1
        assert edges.right == 2
        assert edges.bottom == 3
        assert edges.left == 4

    def test_border_resolve_zero(self):
        border = Border.zero()
        edges = border.resolve()
        assert edges == Edges.zero()
