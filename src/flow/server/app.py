# src/flow/server/app.py
"""FastAPI application factory for Flow apps (Renderer Protocol)."""

from __future__ import annotations

import inspect
import json
import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse

from flow.renderer import HTMLRenderer, Renderer
from flow.rpc import RpcRegistry
from flow.rpc.encoder import flow_json_dumps
from flow.runtime.registry import ElementRegistry

# Client-side JavaScript for event delegation and live updates
CLIENT_JS = """
const socket = new WebSocket(`ws://${location.host}/ws`);

// Connection state
let connected = false;

socket.onopen = () => {
    connected = true;
    console.log('[Flow] WebSocket connected');
};

socket.onclose = () => {
    connected = false;
    console.log('[Flow] WebSocket disconnected');
};

socket.onerror = (e) => {
    console.error('[Flow] WebSocket error:', e);
};

// Handle incoming patches from server
socket.onmessage = (event) => {
    const patch = JSON.parse(event.data);
    console.log('[Flow] Received patch:', patch);
    if (patch.op === 'replace') {
        const el = document.getElementById(patch.target_id);
        if (el) {
            el.outerHTML = patch.html;
        } else {
            console.warn('[Flow] Element not found:', patch.target_id);
        }
    } else if (patch.op === 'update_root') {
        const root = document.getElementById('flow-root');
        if (root) {
            root.innerHTML = patch.html;
        }
    }
};

// Event delegation - handle clicks
document.addEventListener('click', (e) => {
    // Find the closest element with a flow ID
    const target = e.target.closest('[id^="flow-"]');
    if (target && connected) {
        console.log('[Flow] Click on:', target.id);
        socket.send(JSON.stringify({
            type: 'click',
            target_id: target.id
        }));
    }
});

// Handle input changes (for Signal binding)
document.addEventListener('input', (e) => {
    const target = e.target.closest('[id^="flow-"]');
    if (target && connected) {
        console.log('[Flow] Input on:', target.id, 'value:', target.value);
        socket.send(JSON.stringify({
            type: 'input',
            target_id: target.id,
            value: target.value
        }));
    }
});

// Handle change events (for select, checkbox, etc.)
document.addEventListener('change', (e) => {
    const target = e.target.closest('[id^="flow-"]');
    if (target && connected) {
        console.log('[Flow] Change on:', target.id, 'value:', target.value);
        socket.send(JSON.stringify({
            type: 'change',
            target_id: target.id,
            value: target.value
        }));
    }
});

// Handle form submissions
document.addEventListener('submit', (e) => {
    e.preventDefault();
    const target = e.target.closest('[id^="flow-"]');
    if (target && connected) {
        socket.send(JSON.stringify({
            type: 'submit',
            target_id: target.id
        }));
    }
});

// Handle keydown for Enter key in inputs
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const target = e.target.closest('input[id^="flow-"]');
        if (target && connected) {
            console.log('[Flow] Enter key on:', target.id);
            socket.send(JSON.stringify({
                type: 'enter',
                target_id: target.id,
                value: target.value
            }));
        }
    }
});
"""


class AppState:
    """Shared state for the Flow app."""

    def __init__(self) -> None:
        self.root_component: Any = None
        self.root_element: Any = None  # Cached element tree
        self.registry: ElementRegistry = ElementRegistry()
        self.renderer: Renderer = HTMLRenderer()
        self.lock = threading.Lock()


def create_app(
    root_component: Any,  # Callable that returns Element
    renderer: Renderer | None = None,
) -> FastAPI:
    """
    Create a FastAPI app that serves a Flow component.

    Args:
        root_component: An async function decorated with @component
        renderer: Optional Renderer (defaults to HTMLRenderer)

    Returns:
        A configured FastAPI application
    """
    app = FastAPI(title="Flow App")
    state = AppState()
    state.root_component = root_component
    state.renderer = renderer or HTMLRenderer()

    async def _get_or_create_root() -> Any:
        """Get the cached root element or create it."""
        with state.lock:
            if state.root_element is None:
                # Create the element tree once
                state.root_element = await state.root_component()
                # Register all elements for event routing
                state.registry.register_tree(state.root_element)
            return state.root_element

    async def _re_render_root() -> Any:
        """Re-render the root component and update registry."""
        with state.lock:
            # Clear old registry
            state.registry.clear()
            # Create new element tree
            state.root_element = await state.root_component()
            # Register all elements
            state.registry.register_tree(state.root_element)
            return state.root_element

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Serve the initial HTML page."""
        # Get or create the shared element tree
        root = await _get_or_create_root()

        # Render using Renderer Protocol
        full_html = state.renderer.render(root)

        html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flow App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="flow-root">{full_html}</div>
    <script>{CLIENT_JS}</script>
</body>
</html>
"""
        return HTMLResponse(content=html_doc)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle WebSocket connections for live updates."""
        await websocket.accept()

        try:
            while True:
                # Receive event from client
                data = await websocket.receive_json()
                event_type = data.get("type", "")
                target_id_str = data.get("target_id", "")

                # Parse element ID from "flow-12345" format
                if not target_id_str.startswith("flow-"):
                    continue

                try:
                    element_id = int(target_id_str[5:])  # Remove "flow-" prefix
                except ValueError:
                    continue

                # Handle different event types
                if event_type == "click":
                    handler = state.registry.get_handler(element_id, "click")
                    if handler:
                        if inspect.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()

                        # Re-render and send update
                        root = await _re_render_root()
                        html = state.renderer.render(root)
                        await websocket.send_json({"op": "update_root", "html": html})

                elif event_type == "input":
                    # Handle input for Signal binding
                    element = state.registry.get(element_id)
                    if element and hasattr(element, "bind") and element.bind is not None:
                        # Update the bound Signal
                        element.bind.value = data.get("value", "")

                elif event_type == "change":
                    handler = state.registry.get_handler(element_id, "change")
                    if handler:
                        value = data.get("value", "")
                        if inspect.iscoroutinefunction(handler):
                            await handler(value)  # type: ignore[call-arg]
                        else:
                            handler(value)  # type: ignore[call-arg]

                        # Re-render and send update
                        root = await _re_render_root()
                        html = state.renderer.render(root)
                        await websocket.send_json({"op": "update_root", "html": html})

                elif event_type == "enter":
                    # Enter key pressed in input - trigger click on nearby button
                    # This is a common pattern for form submission
                    pass  # Will be handled by the form logic

        except Exception:  # noqa: S110 - WebSocket disconnect is expected
            pass  # Connection closed

    @app.post("/api/rpc/{func_name}")
    async def rpc_handler(func_name: str, request: Request) -> JSONResponse:
        """Handle RPC calls from the client with robust serialization."""
        target_func = RpcRegistry.get(func_name)

        if target_func is None:
            raise HTTPException(status_code=404, detail=f"RPC function '{func_name}' not found")

        # Parse the request body as JSON
        try:
            data = await request.json()
        except Exception:
            data = {}

        # Call the function with the provided arguments
        result = await target_func(**data)

        # Serialize with FlowJSONEncoder (handles datetime, UUID, dataclasses, etc.)
        json_content = flow_json_dumps(result)

        return JSONResponse(
            content=json.loads(json_content),  # FastAPI requires dict, not string
            media_type="application/json",
        )

    return app


def run_app(
    root_component: Any,
    host: str = "127.0.0.1",
    port: int = 8000,
    renderer: Renderer | None = None,
) -> None:
    """Run a Flow app with uvicorn."""
    import uvicorn

    app = create_app(root_component, renderer=renderer)
    uvicorn.run(app, host=host, port=port)
