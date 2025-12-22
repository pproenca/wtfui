from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.tui.layout.style import FlexStyle
    from wtfui.tui.layout.types import Size


class MeasureMode(Enum):
    UNDEFINED = "undefined"
    EXACTLY = "exactly"
    AT_MOST = "at-most"


@dataclass(frozen=True)
class CachedMeasurement:
    available_width: float
    available_height: float
    width_mode: MeasureMode
    height_mode: MeasureMode
    computed_width: float
    computed_height: float


class BaselineFunc(Protocol):
    def __call__(self, width: float, height: float) -> float: ...


@dataclass
class LayoutResult:
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


@dataclass
class LayoutNode:
    style: FlexStyle
    children: list[LayoutNode] = field(default_factory=list)
    parent: LayoutNode | None = field(default=None, repr=False)

    measure_func: Callable[..., Size] | None = field(default=None)

    baseline_func: BaselineFunc | None = field(default=None)

    cached_measurement: CachedMeasurement | None = field(default=None)

    layout: LayoutResult = field(default_factory=LayoutResult)

    _dirty: bool = field(default=True, repr=False)

    def add_child(self, child: LayoutNode) -> None:
        if self.measure_func is not None:
            raise ValueError("Cannot add children to a measured node")

        if child is self:
            raise ValueError("Cannot add node as its own child (circular reference)")

        ancestor = self.parent
        while ancestor is not None:
            if ancestor is child:
                raise ValueError("Cannot add ancestor as child (circular reference)")
            ancestor = ancestor.parent

        child.parent = self
        self.children.append(child)
        self.mark_dirty()

    def remove_child(self, child: LayoutNode) -> None:
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.mark_dirty()

    def mark_dirty(self) -> None:
        if self._dirty:
            return
        self._dirty = True
        self.cached_measurement = None
        if self.parent is not None:
            self.parent.mark_dirty()

    def is_dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False

    def is_layout_boundary(self) -> bool:
        return self.style.width.is_defined() and self.style.height.is_defined()

    def has_baseline_func(self) -> bool:
        return self.baseline_func is not None

    def invalidate_cache(self) -> None:
        self.cached_measurement = None

    def get_baseline(self, width: float, height: float) -> float | None:
        if self.baseline_func is not None:
            return self.baseline_func(width, height)
        return None

    def hit_test(self, x: float, y: float) -> LayoutNode | None:
        if not (
            self.layout.x <= x < self.layout.x + self.layout.width
            and self.layout.y <= y < self.layout.y + self.layout.height
        ):
            return None

        for child in reversed(self.children):
            local_x = x - self.layout.x
            local_y = y - self.layout.y
            hit = child.hit_test(local_x, local_y)
            if hit is not None:
                return hit

        return self
