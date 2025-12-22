from typing import TYPE_CHECKING, Any

from wtfui.core.context import reset_runtime, set_current_runtime
from wtfui.tui.renderer import ConsoleRenderer
from wtfui.tui.renderer.input import MouseEvent
from wtfui.tui.runtime import TUIRuntime
from wtfui.tui.testing.locator import SemanticLocator
from wtfui.tui.testing.snapshot import snapshot as take_snapshot
from wtfui.tui.testing.stabilize import stabilize

if TYPE_CHECKING:
    from collections.abc import Callable


class ElementLocator:
    def __init__(
        self,
        driver: TUITestDriver,
        text: str,
        partial: bool = False,
    ) -> None:
        self._driver = driver
        self._text = text
        self._partial = partial

    def _find_node(self):
        self._driver._refresh_render_node()

        if self._driver._render_node is None:
            raise RuntimeError("Driver not started. Call start() first.")
        if self._driver.runtime is None:
            raise RuntimeError("Driver not started. Call start() first.")

        locator = SemanticLocator(
            render_tree=self._driver._render_node,
            element_to_layout=self._driver.runtime._element_to_layout,
        )
        return locator.find_by_text(self._text, partial=self._partial)

    def _get_center(self):
        node = self._find_node()
        if node is None:
            raise ValueError(f"Element with text '{self._text}' not found")

        if self._driver._render_node is None:
            raise RuntimeError("Driver not started. Call start() first.")
        if self._driver.runtime is None:
            raise RuntimeError("Driver not started. Call start() first.")

        locator = SemanticLocator(
            render_tree=self._driver._render_node,
            element_to_layout=self._driver.runtime._element_to_layout,
        )
        return locator.get_center(node)

    async def click(self) -> None:
        if self._driver.runtime is None:
            raise RuntimeError("Driver not started. Call start() first.")

        x, y = self._get_center()

        event = MouseEvent(x=int(x), y=int(y), button=0, pressed=True)
        await self._driver.runtime._handle_event(event)

        await self._driver.stabilize()


class TUITestDriver:
    def __init__(
        self,
        app_factory: Callable[[], Any],
        width: int = 80,
        height: int = 24,
    ) -> None:
        self._app_factory = app_factory
        self._width = width
        self._height = height
        self.runtime: TUIRuntime | None = None
        self._render_node = None
        self._runtime_token = None

    async def start(self) -> None:
        self.runtime = TUIRuntime(
            app_factory=self._app_factory,
            fps=60,
            mouse=True,
        )
        self.runtime.running = True

        self.runtime.renderer = ConsoleRenderer(
            width=self._width,
            height=self._height,
        )

        self._runtime_token = set_current_runtime(self.runtime)

        self.runtime.element_tree = await self.runtime._resolve_app()

        self.runtime._update_layout()

        self._refresh_render_node()

        self.runtime._render_frame()

        await self.stabilize()

    def _refresh_render_node(self) -> None:
        if (
            self.runtime is not None
            and self.runtime.element_tree is not None
            and self.runtime.layout_root is not None
        ):
            from wtfui.tui.builder import RenderTreeBuilder

            self._render_node = RenderTreeBuilder().build_with_layout(
                self.runtime.element_tree, self.runtime.layout_root
            )

    def snapshot(self) -> str:
        if self.runtime is None or self.runtime.renderer is None:
            raise RuntimeError("Driver not started. Call start() first.")

        return take_snapshot(self.runtime.renderer)

    def get_by_text(self, text: str, partial: bool = False) -> ElementLocator:
        return ElementLocator(self, text, partial)

    async def stabilize(self, max_wait: float = 1.0) -> bool:
        result = await stabilize(max_wait)

        if self.runtime is not None:
            self.runtime._update_layout()

            self.runtime._render_frame()

        self._refresh_render_node()

        return result

    async def press(self, key: str) -> None:
        from wtfui.tui.renderer.input import KeyEvent

        if self.runtime is None:
            raise RuntimeError("Driver not started. Call start() first.")

        event = KeyEvent(key=key)
        await self.runtime._handle_event(event)
        await self.stabilize()

    async def type(self, text: str) -> None:
        for char in text:
            await self.press(char)

    def stop(self) -> None:
        if self._runtime_token is not None:
            reset_runtime(self._runtime_token)
            self._runtime_token = None

        if self.runtime is not None:
            self.runtime._dispose_layout()
            self.runtime.running = False
