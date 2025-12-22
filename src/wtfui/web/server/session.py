import asyncio
import inspect
import threading
from typing import TYPE_CHECKING, Any

from wtfui.core.registry import ElementRegistry
from wtfui.web.renderer import HTMLRenderer

if TYPE_CHECKING:
    from wtfui.core.element import Element
    from wtfui.core.protocol import Renderer


CLIENT_JS = """
const socket = new WebSocket(`ws://${location.host}/ws`);

// Handle incoming patches
socket.onmessage = (event) => {
    const patch = JSON.parse(event.data);
    if (patch.op === 'replace') {
        const el = document.getElementById(patch.target_id);
        if (el) el.outerHTML = patch.html;
    }
};

// Event delegation - send events to server
document.addEventListener('click', (e) => {
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'click',
            target_id: target.id
        }));
    }
});

// Input change events
document.addEventListener('change', (e) => {
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'change',
            target_id: target.id,
            value: target.value
        }));
    }
});

// Input events for live binding
document.addEventListener('input', (e) => {
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'input',
            target_id: target.id,
            value: target.value
        }));
    }
});
"""


class LiveSession:
    def __init__(
        self,
        root_component: Element,
        websocket: Any,
        renderer: Renderer | None = None,
    ) -> None:
        self.root_component = root_component
        self.socket = websocket
        self.renderer = renderer or HTMLRenderer()
        self.queue: asyncio.Queue[Element] = asyncio.Queue()
        self._running = False
        self._lock = threading.Lock()

        self._registry = ElementRegistry()
        self._registry.register_tree(root_component)

    def queue_update(self, node: Element) -> None:
        self.queue.put_nowait(node)

    async def send_initial_render(self) -> None:
        full_html = self.renderer.render(self.root_component)

        html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="wtfui-root">{full_html}</div>
    <script>{CLIENT_JS}</script>
</body>
</html>
"""
        await self.socket.send_text(html_doc)

    async def start(self) -> None:
        await self.socket.accept()
        await self.send_initial_render()

        self._running = True

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._incoming_loop())
            tg.create_task(self._outgoing_loop())

    async def _incoming_loop(self) -> None:
        while self._running:
            try:
                data = await self.socket.receive_json()
                await self._handle_event(data)
            except Exception:
                self._running = False
                break

    async def _outgoing_loop(self) -> None:
        while self._running:
            try:
                node = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                html = await asyncio.to_thread(self.renderer.render, node)

                patch = {
                    "op": "replace",
                    "target_id": f"wtfui-{id(node)}",
                    "html": html,
                }
                await self.socket.send_json(patch)

            except TimeoutError:
                continue
            except Exception:
                self._running = False
                break

    async def _handle_event(self, data: dict[str, Any]) -> None:
        event_type = data.get("type", "")
        target_id_str = data.get("target_id", "")

        if not target_id_str.startswith("wtfui-"):
            return

        try:
            element_id = int(target_id_str[6:])
        except ValueError:
            return

        handler = self._registry.get_handler(element_id, event_type)
        if handler is None:
            return

        if inspect.iscoroutinefunction(handler):
            await handler()
        else:
            handler()

    def stop(self) -> None:
        with self._lock:
            self._running = False
