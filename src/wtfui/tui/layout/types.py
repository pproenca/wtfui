from dataclasses import dataclass
from enum import Enum


class DimensionUnit(Enum):
    AUTO = "auto"
    POINTS = "px"
    PERCENT = "%"
    MIN_CONTENT = "min-content"
    MAX_CONTENT = "max-content"
    FIT_CONTENT = "fit-content"


@dataclass(frozen=True, slots=True)
class Dimension:
    value: float | None = None
    _unit: DimensionUnit = DimensionUnit.AUTO

    @classmethod
    def auto(cls) -> Dimension:
        return cls(None, DimensionUnit.AUTO)

    @classmethod
    def points(cls, value: float) -> Dimension:
        return cls(value, DimensionUnit.POINTS)

    @classmethod
    def percent(cls, value: float) -> Dimension:
        return cls(value, DimensionUnit.PERCENT)

    @classmethod
    def min_content(cls) -> Dimension:
        return cls(None, DimensionUnit.MIN_CONTENT)

    @classmethod
    def max_content(cls) -> Dimension:
        return cls(None, DimensionUnit.MAX_CONTENT)

    @classmethod
    def fit_content(cls, max_size: float | None = None) -> Dimension:
        return cls(max_size, DimensionUnit.FIT_CONTENT)

    @property
    def unit(self) -> str:
        return self._unit.value

    def is_auto(self) -> bool:
        return self._unit == DimensionUnit.AUTO

    def is_intrinsic(self) -> bool:
        return self._unit in (
            DimensionUnit.MIN_CONTENT,
            DimensionUnit.MAX_CONTENT,
            DimensionUnit.FIT_CONTENT,
        )

    def is_defined(self) -> bool:
        return self._unit != DimensionUnit.AUTO and self.value is not None

    def resolve(self, parent_value: float) -> float | None:
        if self._unit == DimensionUnit.POINTS:
            return self.value
        elif self._unit == DimensionUnit.PERCENT and self.value is not None:
            return (self.value / 100) * parent_value
        return None


@dataclass(frozen=True, slots=True)
class Size:
    width: float = 0
    height: float = 0

    @classmethod
    def zero(cls) -> Size:
        return cls(0, 0)


@dataclass(frozen=True, slots=True)
class Point:
    x: float = 0
    y: float = 0


@dataclass(frozen=True, slots=True)
class Rect:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Edges:
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> Edges:
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, horizontal: float = 0, vertical: float = 0) -> Edges:
        return cls(vertical, horizontal, vertical, horizontal)

    @classmethod
    def zero(cls) -> Edges:
        return cls(0, 0, 0, 0)

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom


@dataclass(frozen=True, slots=True)
class Border:
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> Border:
        return cls(value, value, value, value)

    @classmethod
    def zero(cls) -> Border:
        return cls(0, 0, 0, 0)

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom

    def resolve(self) -> Edges:
        return Edges(
            top=self.top,
            right=self.right,
            bottom=self.bottom,
            left=self.left,
        )


@dataclass(frozen=True, slots=True)
class Spacing:
    top: Dimension | None = None
    right: Dimension | None = None
    bottom: Dimension | None = None
    left: Dimension | None = None

    def __post_init__(self) -> None:
        if self.top is None:
            object.__setattr__(self, "top", Dimension.auto())
        if self.right is None:
            object.__setattr__(self, "right", Dimension.auto())
        if self.bottom is None:
            object.__setattr__(self, "bottom", Dimension.auto())
        if self.left is None:
            object.__setattr__(self, "left", Dimension.auto())

    @classmethod
    def all(cls, value: Dimension) -> Spacing:
        return cls(value, value, value, value)

    @classmethod
    def zero(cls) -> Spacing:
        zero = Dimension.points(0)
        return cls(zero, zero, zero, zero)

    def left_is_auto(self) -> bool:
        return self.left is not None and self.left.is_auto()

    def right_is_auto(self) -> bool:
        return self.right is not None and self.right.is_auto()

    def top_is_auto(self) -> bool:
        return self.top is not None and self.top.is_auto()

    def bottom_is_auto(self) -> bool:
        return self.bottom is not None and self.bottom.is_auto()

    def horizontal_is_auto(self) -> bool:
        return self.left_is_auto() and self.right_is_auto()

    def vertical_is_auto(self) -> bool:
        return self.top_is_auto() and self.bottom_is_auto()

    def resolve(self, width: float, height: float) -> Edges:
        return Edges(
            top=self.top.resolve(height) or 0 if self.top else 0,
            right=self.right.resolve(width) or 0 if self.right else 0,
            bottom=self.bottom.resolve(height) or 0 if self.bottom else 0,
            left=self.left.resolve(width) or 0 if self.left else 0,
        )


LAYOUT_EPSILON = 0.001


def approx_equal(a: float, b: float, epsilon: float = LAYOUT_EPSILON) -> bool:
    return abs(a - b) < epsilon


def snap_to_pixel(value: float, scale: float = 1.0) -> float:
    return round(value * scale) / scale


def parse_dimension(value: float | str | None) -> Dimension:
    if value is None:
        return Dimension.auto()
    if isinstance(value, int | float):
        return Dimension.points(float(value))
    if isinstance(value, str):
        if value.endswith("%"):
            return Dimension.percent(float(value[:-1]))
        return Dimension.points(float(value.replace("px", "")))
    return Dimension.auto()


def parse_spacing(value: float | tuple[float, ...] | None) -> Spacing:
    if value is None:
        return Spacing()
    if isinstance(value, int | float):
        d = Dimension.points(float(value))
        return Spacing(top=d, right=d, bottom=d, left=d)
    if isinstance(value, tuple):
        if len(value) == 4:
            return Spacing(
                top=Dimension.points(value[0]),
                right=Dimension.points(value[1]),
                bottom=Dimension.points(value[2]),
                left=Dimension.points(value[3]),
            )
        if len(value) == 2:
            v = Dimension.points(value[0])
            h = Dimension.points(value[1])
            return Spacing(top=v, right=h, bottom=v, left=h)
        if len(value) == 1:
            d = Dimension.points(value[0])
            return Spacing(top=d, right=d, bottom=d, left=d)
    return Spacing()


def parse_css_dimension(value: str | int | float) -> int:
    import re

    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    cleaned = re.sub(r"(px|em|rem|%|pt)$", "", str(value).strip())
    try:
        return int(float(cleaned))
    except ValueError:
        return 0
