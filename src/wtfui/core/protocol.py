from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wtfui.core.element import Element


@dataclass
class RenderNode:
    tag: str
    element_id: int
    props: dict[str, Any] = field(default_factory=dict)
    children: list[RenderNode] = field(default_factory=list)

    text_content: str | None = None
    label: str | None = None

    layout: Any = None


class Renderer(ABC):
    @abstractmethod
    def render(self, element: Element) -> Any: ...

    @abstractmethod
    def render_node(self, node: RenderNode) -> Any: ...

    @abstractmethod
    def render_text(self, content: str) -> Any: ...
