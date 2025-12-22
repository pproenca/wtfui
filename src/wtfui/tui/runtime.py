import asyncio
import contextlib
import inspect
import sys
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.element import Element
    from wtfui.tui.layout.node import LayoutNode
    from wtfui.tui.layout.reactive import ReactiveLayoutNode
    from wtfui.tui.renderer.input import KeyEvent, MouseEvent, ResizeEvent

from wtfui.core.registry import ElementRegistry
from wtfui.tui.adapter import ReactiveLayoutAdapter


class TUIRuntime:
    def __init__(
        self,
        app_factory: Callable[[], Any],
        *,
        fps: int = 60,
        mouse: bool = True,
        on_key: Callable[[str], None] | None = None,
        inline: bool = False,
    ) -> None:
        if fps <= 0:
            msg = f"fps must be positive, got {fps}"
            raise ValueError(msg)

        self.app_factory = app_factory
        self.fps = fps
        self.mouse = mouse
        self.on_key = on_key
        self.inline = inline

        self.element_tree = None
        self.layout_root = None
        self.reactive_layout = None
        self._dirty_callbacks = []

        self._layout_to_element = {}
        self._element_to_layout = {}

        self._registry = ElementRegistry()

        self.event_queue: asyncio.Queue[KeyEvent | MouseEvent] = asyncio.Queue()

        self._loop: asyncio.AbstractEventLoop | None = None

        self.renderer: Any = None

        self.render_lock = threading.RLock()
        self._term_size_lock = threading.Lock()
        self._focus_lock = threading.Lock()
        self._term_size = (80, 24)
        self.is_dirty = True
        self.running = False
        self.needs_rebuild = False

        self._focused_element_id: int | None = None

    @property
    def focused_element_id(self) -> int | None:
        with self._focus_lock:
            return self._focused_element_id

    @focused_element_id.setter
    def focused_element_id(self, value: int | None) -> None:
        with self._focus_lock:
            self._focused_element_id = value

    def set_focus(self, element_id: int | None) -> None:
        with self._focus_lock:
            self._focused_element_id = element_id
        self.is_dirty = True

    def _register_sigwinch_handler(self) -> Any:
        import signal
        import sys

        if sys.platform == "win32":
            return None

        from wtfui.tui.renderer.input import ResizeEvent
        from wtfui.tui.renderer.terminal import get_terminal_size

        def on_sigwinch(signum: int, frame: object) -> None:
            width, height = get_terminal_size()
            event = ResizeEvent(width=width, height=height)

            if self._loop is not None:
                self._loop.call_soon_threadsafe(self.event_queue.put_nowait, event)

        old_handler = signal.signal(signal.SIGWINCH, on_sigwinch)
        return old_handler

    @property
    def term_width(self) -> int:
        return self._term_size[0]

    @term_width.setter
    def term_width(self, value: int) -> None:
        with self._term_size_lock:
            self._term_size = (value, self._term_size[1])

    @property
    def term_height(self) -> int:
        return self._term_size[1]

    @term_height.setter
    def term_height(self, value: int) -> None:
        with self._term_size_lock:
            self._term_size = (self._term_size[0], value)

    def _input_worker(self) -> None:
        import select

        from wtfui.tui.renderer.input import (
            ESCAPE,
            parse_input_sequence,
        )

        while self.running:
            try:
                char = sys.stdin.read(1)
                if not char:
                    continue

                if char == ESCAPE:
                    extra = ""

                    while select.select([sys.stdin], [], [], 0.05)[0]:
                        extra += sys.stdin.read(1)
                    char = char + extra

                event = parse_input_sequence(char)

                if self._loop is not None:
                    self._loop.call_soon_threadsafe(self.event_queue.put_nowait, event)
            except OSError:
                pass

    async def _consume_events(self) -> None:
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=0.1,
                )
                await self._handle_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _handle_event(self, event: KeyEvent | MouseEvent | ResizeEvent) -> None:
        from wtfui.tui.renderer.input import KeyEvent, MouseEvent, ResizeEvent

        match event:
            case ResizeEvent(width=w, height=h):
                with self.render_lock:
                    self.term_width = w
                    self.term_height = h

                    if self.renderer is not None:
                        clear_seq = self.renderer.resize(w, h)
                        sys.stdout.write(clear_seq)
                        sys.stdout.flush()

                self._update_layout()

            case MouseEvent(x=x, y=y, pressed=pressed):
                if self.renderer is not None:
                    with self.render_lock:
                        if self.renderer.update_mouse(x, y):
                            self.is_dirty = True

                if pressed and self.layout_root is not None:
                    hit_node = self.layout_root.hit_test(x, y)
                    if hit_node is not None:
                        element = self._layout_to_element.get(id(hit_node))
                        if element is not None:
                            if getattr(element, "focusable", False):
                                self.set_focus(id(element))

                            handler = self._registry.get_handler(id(element), "click")
                            if handler is not None:
                                if inspect.iscoroutinefunction(handler):
                                    await handler()
                                else:
                                    handler()
                                self.is_dirty = True

            case KeyEvent(key=key, ctrl=ctrl):
                if self.focused_element_id is not None:
                    element = self._registry.get(self.focused_element_id)
                    if element is not None:
                        handler = element.props.get("on_keydown")
                        if handler is not None:
                            if inspect.iscoroutinefunction(handler):
                                await handler(key)
                            else:
                                handler(key)
                            self.is_dirty = True

                if self.on_key is not None:
                    try:
                        self.on_key(key)
                    except Exception as e:
                        sys.stderr.write(f"Error in on_key callback: {e}\n")

                if key == "q" or (key == "c" and ctrl):
                    self.running = False

    async def _resolve_app(self) -> Any:
        from wtfui.core.context import reset_parent, set_current_parent

        class _CaptureParent:
            def __init__(self) -> None:
                self.children: list[Any] = []

            def invalidate_layout(self) -> None:
                pass

        capture = _CaptureParent()
        token = set_current_parent(capture)

        try:
            if inspect.iscoroutinefunction(self.app_factory):
                await self.app_factory()
            else:
                result = self.app_factory()

                if inspect.iscoroutine(result):
                    await result
        finally:
            reset_parent(token)

        if capture.children:
            return capture.children[0]
        return None

    async def _main_loop(self) -> None:
        from wtfui.core.context import reset_runtime, set_current_runtime

        self._loop = asyncio.get_running_loop()

        runtime_token = set_current_runtime(self)

        try:
            self.element_tree = await self._resolve_app()

            self._update_layout()

            event_task = asyncio.create_task(self._consume_events())

            frame_delay = 1.0 / self.fps

            try:
                while self.running:
                    if self.is_dirty:
                        self._update_layout()
                        await self._render_frame_async()

                    await asyncio.sleep(frame_delay)
            finally:
                event_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await event_task
        finally:
            reset_runtime(runtime_token)

    def _dispose_layout(self) -> None:
        with self.render_lock:
            for unsub in self._dirty_callbacks:
                unsub()
            self._dirty_callbacks.clear()

            if self.reactive_layout is not None:
                stack = [self.reactive_layout]
                while stack:
                    node = stack.pop()
                    node.dispose()
                    stack.extend(node.children)
                self.reactive_layout = None

            self.layout_root = None

    def _hook_dirty_callback(self, node: ReactiveLayoutNode) -> None:
        def dirty_callback() -> None:
            self.is_dirty = True

        for signal in node.style_signals.values():
            unsub = signal.subscribe(dirty_callback)
            self._dirty_callbacks.append(unsub)

        for child in node.children:
            self._hook_dirty_callback(child)

    def _build_layout_element_map(
        self,
        element: Element,
        layout_node: LayoutNode,
        parent_layout: LayoutNode | None = None,
    ) -> None:
        layout_node.parent = parent_layout

        self._layout_to_element[id(layout_node)] = element

        self._element_to_layout[id(element)] = layout_node

        for elem_child, layout_child in zip(element.children, layout_node.children, strict=False):
            self._build_layout_element_map(elem_child, layout_child, layout_node)

    def _update_layout(self) -> None:
        from wtfui.tui.layout.compute import compute_layout
        from wtfui.tui.layout.types import Size

        with self.render_lock:
            if self.element_tree is None:
                return
            element_tree = self.element_tree

            if self.needs_rebuild:
                if self.reactive_layout is not None:
                    stack = [self.reactive_layout]
                    while stack:
                        node = stack.pop()
                        node.dispose()
                        stack.extend(node.children)

                for unsub in self._dirty_callbacks:
                    unsub()
                self._dirty_callbacks.clear()

                self.reactive_layout = None
                self.needs_rebuild = False

            if self.reactive_layout is None:
                self.reactive_layout = ReactiveLayoutAdapter().to_reactive_layout_node(element_tree)
                self._hook_dirty_callback(self.reactive_layout)

            if not self.reactive_layout.is_dirty():
                return

            self.layout_root = self.reactive_layout.to_layout_node()

            self._layout_to_element.clear()
            self._element_to_layout.clear()
            self._build_layout_element_map(element_tree, self.layout_root, None)

            self._registry.clear()
            self._registry.register_tree(element_tree)

            available_height = 100000.0 if self.inline else float(self.term_height)
            compute_layout(
                self.layout_root,
                available=Size(width=self.term_width, height=available_height),
            )

            if self.inline and self.renderer is not None:
                content_height = int(self.layout_root.layout.height)
                content_height = max(1, content_height)
                if self.renderer.height != content_height:
                    self.renderer.resize(self.term_width, content_height, clear=False)

            self.reactive_layout.clear_dirty_recursive()
            self.is_dirty = True

    def _render_frame(self) -> None:
        if self.renderer is None or self.layout_root is None:
            return

        if self.element_tree is None:
            return

        with self.render_lock:
            if self.needs_rebuild:
                return

            self.renderer.clear()

            from wtfui.tui.builder import RenderTreeBuilder

            render_node = RenderTreeBuilder().build_with_layout(self.element_tree, self.layout_root)

            self.renderer.render_node_with_layout(render_node)

            ansi_output = self.renderer.flush(inline=self.inline)

            output_stream = sys.__stdout__ if sys.__stdout__ is not None else sys.stdout
            output_stream.write(ansi_output)
            output_stream.flush()

            self.is_dirty = False

    async def _render_frame_async(self) -> None:
        await asyncio.to_thread(self._render_frame)

    def start(self) -> None:
        from contextlib import ExitStack

        from wtfui.tui.renderer import ConsoleRenderer
        from wtfui.tui.renderer.output import OutputRedirector
        from wtfui.tui.renderer.terminal import TerminalContext, get_terminal_size

        self.term_width, self.term_height = get_terminal_size()

        with ExitStack() as stack:
            stack.enter_context(
                TerminalContext(
                    width=self.term_width,
                    height=self.term_height,
                    mouse=self.mouse,
                    inline=self.inline,
                )
            )

            self.renderer = ConsoleRenderer(self.term_width, self.term_height)

            if self.inline:
                stack.enter_context(OutputRedirector(self.renderer, self.render_lock))

            self.running = True

            old_sigwinch_handler = self._register_sigwinch_handler()

            input_thread = threading.Thread(
                target=self._input_worker,
                daemon=True,
                name="TUIRuntime-Input",
            )
            input_thread.start()

            try:
                asyncio.run(self._main_loop())
            except KeyboardInterrupt:
                pass
            finally:
                self.running = False
                self._dispose_layout()
                self._loop = None

                if old_sigwinch_handler is not None:
                    import signal

                    signal.signal(signal.SIGWINCH, old_sigwinch_handler)


def run_tui_app(component: Callable[[], Any]) -> None:
    runtime = TUIRuntime(component)
    runtime.start()


run = run_tui_app
