# src/flow/server/session.py
"""LiveSession - No-GIL optimized live rendering manager."""

from __future__ import annotations

import asyncio
import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from flow.renderer import HTMLRenderer, Renderer
from flow.runtime.registry import ElementRegistry

if TYPE_CHECKING:
    from flow.element import Element

# Thread pool for No-GIL diff calculation
# In Python 3.14+, this truly runs in parallel
_diff_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="flow-diff")

# Client-side JS for event delegation and patch receiving
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
    const target = e.target.closest('[id^="flow-"]');
    if (target && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'click',
            target_id: target.id
        }));
    }
});

// Input change events
document.addEventListener('change', (e) => {
    const target = e.target.closest('[id^="flow-"]');
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
    const target = e.target.closest('[id^="flow-"]');
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
    """
    Manages the live connection between a Python UI tree and a browser.

    Optimized for Python 3.14+ No-GIL builds:
    - Diff calculation runs in ThreadPoolExecutor (truly parallel)
    - AsyncIO handles I/O only (WebSocket send/receive)
    - Uses Renderer Protocol for Universal Runtime compatibility
    """

    def __init__(
        self,
        root_component: Element,
        websocket: Any,
        renderer: Renderer | None = None,
    ) -> None:
        self.root_component = root_component
        self.socket = websocket
        self.renderer = renderer or HTMLRenderer()  # Swappable!
        self.queue: asyncio.Queue[Element] = asyncio.Queue()
        self._running = False
        self._lock = threading.Lock()

        # Element registry for event routing
        self._registry = ElementRegistry()
        self._registry.register_tree(root_component)

    def queue_update(self, node: Element) -> None:
        """Queue a node for re-rendering and sending to client."""
        self.queue.put_nowait(node)

    async def send_initial_render(self) -> None:
        """Send the initial full HTML render to the client."""
        # Renderer Protocol: Not hardcoded to_html!
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
    <div id="flow-root">{full_html}</div>
    <script>{CLIENT_JS}</script>
</body>
</html>
"""
        await self.socket.send_text(html_doc)

    async def start(self) -> None:
        """Start the live session loops."""
        await self.socket.accept()
        await self.send_initial_render()

        self._running = True

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._incoming_loop())
            tg.create_task(self._outgoing_loop())

    async def _incoming_loop(self) -> None:
        """Handle incoming events from the browser."""
        while self._running:
            try:
                data = await self.socket.receive_json()
                await self._handle_event(data)
            except Exception:
                self._running = False
                break

    async def _outgoing_loop(self) -> None:
        """Send queued updates to the browser (No-GIL optimized)."""
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                node = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # NO-GIL OPTIMIZATION: Run diff/render in thread pool
                # This is truly parallel in Python 3.14+ free-threaded builds
                html = await loop.run_in_executor(
                    _diff_executor,
                    self.renderer.render,  # Renderer Protocol!
                    node,
                )

                patch = {
                    "op": "replace",
                    "target_id": f"flow-{id(node)}",
                    "html": html,
                }
                await self.socket.send_json(patch)

            except TimeoutError:
                continue
            except Exception:
                self._running = False
                break

    async def _handle_event(self, data: dict[str, Any]) -> None:
        """Route browser event to appropriate Python handler."""
        event_type = data.get("type", "")
        target_id_str = data.get("target_id", "")

        # Parse element ID from "flow-12345" format
        if not target_id_str.startswith("flow-"):
            return

        try:
            element_id = int(target_id_str[5:])  # Remove "flow-" prefix
        except ValueError:
            return

        # Find handler in registry
        handler = self._registry.get_handler(element_id, event_type)
        if handler is None:
            return

        # Execute handler
        # Handle both sync and async handlers
        if inspect.iscoroutinefunction(handler):
            await handler()
        else:
            handler()

        # After handler executes, signal changes may have occurred
        # Those would trigger re-renders via Effect system

    def stop(self) -> None:
        """Stop the session loops (thread-safe)."""
        with self._lock:
            self._running = False
