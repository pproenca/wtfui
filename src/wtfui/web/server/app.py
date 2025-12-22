import inspect
import json
import logging
import threading
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, Response

from wtfui.core.registry import ElementRegistry

if TYPE_CHECKING:
    from wtfui.core.protocol import Renderer
from wtfui.web.renderer import HTMLRenderer
from wtfui.web.rpc import RpcRegistry
from wtfui.web.rpc.encoder import wtfui_json_dumps

logger = logging.getLogger(__name__)

CLIENT_JS = """
const socket = new WebSocket(`ws://${location.host}/ws`);

// Connection state
let connected = false;

socket.onopen = () => {
    connected = true;
    console.log('[wtfui] WebSocket connected');
};

socket.onclose = () => {
    connected = false;
    console.log('[wtfui] WebSocket disconnected');
};

socket.onerror = (e) => {
    console.error('[wtfui] WebSocket error:', e);
};

// Handle incoming patches from server
socket.onmessage = (event) => {
    const patch = JSON.parse(event.data);
    console.log('[wtfui] Received patch:', patch);
    if (patch.op === 'replace') {
        const el = document.getElementById(patch.target_id);
        if (el) {
            el.outerHTML = patch.html;
        } else {
            console.warn('[wtfui] Element not found:', patch.target_id);
        }
    } else if (patch.op === 'update_root') {
        const root = document.getElementById('wtfui-root');
        if (root) {
            root.innerHTML = patch.html;
        }
    }
};

// Event delegation - handle clicks
document.addEventListener('click', (e) => {
    // Find the closest element with a wtfui ID
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && connected) {
        console.log('[wtfui] Click on:', target.id);
        socket.send(JSON.stringify({
            type: 'click',
            target_id: target.id
        }));
    }
});

// Handle input changes (for Signal binding)
document.addEventListener('input', (e) => {
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && connected) {
        console.log('[wtfui] Input on:', target.id, 'value:', target.value);
        socket.send(JSON.stringify({
            type: 'input',
            target_id: target.id,
            value: target.value
        }));
    }
});

// Handle change events (for select, checkbox, etc.)
document.addEventListener('change', (e) => {
    const target = e.target.closest('[id^="wtfui-"]');
    if (target && connected) {
        console.log('[wtfui] Change on:', target.id, 'value:', target.value);
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
    const target = e.target.closest('[id^="wtfui-"]');
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
        const target = e.target.closest('input[id^="wtfui-"]');
        if (target && connected) {
            console.log('[wtfui] Enter key on:', target.id);
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
    def __init__(self) -> None:
        self.root_component: Any = None
        self.root_element: Any = None
        self.registry: ElementRegistry = ElementRegistry()
        self.renderer = HTMLRenderer()
        self._render_lock = threading.Lock()


def create_app(
    root_component: Any,
    renderer: Renderer | None = None,
) -> FastAPI:
    app = FastAPI(title="WtfUI App")
    state = AppState()
    state.root_component = root_component
    state.renderer = renderer or HTMLRenderer()

    async def _get_or_create_root() -> Any:
        with state._render_lock:
            if state.root_element is None:
                state.root_element = await state.root_component()

                state.registry.register_tree(state.root_element)
            return state.root_element

    async def _re_render_root() -> Any:
        with state._render_lock:
            state.registry.clear()

            state.root_element = await state.root_component()

            state.registry.register_tree(state.root_element)
            return state.root_element

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        root = await _get_or_create_root()

        full_html = state.renderer.render(root)

        html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WtfUI App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="wtfui-root">{full_html}</div>
    <script>{CLIENT_JS}</script>
</body>
</html>
"""
        return HTMLResponse(content=html_doc)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()

        try:
            while True:
                data = await websocket.receive_json()
                event_type = data.get("type", "")
                target_id_str = data.get("target_id", "")

                if not target_id_str.startswith("wtfui-"):
                    continue

                try:
                    element_id = int(target_id_str[6:])
                except ValueError:
                    continue

                match event_type:
                    case "click":
                        handler = state.registry.get_handler(element_id, "click")
                        if handler:
                            if inspect.iscoroutinefunction(handler):
                                await handler()
                            else:
                                handler()

                            root = await _re_render_root()
                            html = state.renderer.render(root)
                            await websocket.send_json({"op": "update_root", "html": html})

                    case "input":
                        element = state.registry.get(element_id)
                        if element:
                            bind = getattr(element, "bind", None)
                            if bind is not None:
                                bind.value = data.get("value", "")

                    case "change":
                        handler = state.registry.get_handler(element_id, "change")
                        if handler:
                            value = data.get("value", "")
                            if inspect.iscoroutinefunction(handler):
                                await handler(value)
                            else:
                                handler(value)

                            root = await _re_render_root()
                            html = state.renderer.render(root)
                            await websocket.send_json({"op": "update_root", "html": html})

                    case "enter":
                        pass

        except Exception:
            logger.debug("WebSocket connection closed", exc_info=True)

    @app.post("/api/rpc/{func_name}")
    async def rpc_handler(func_name: str, request: Request) -> JSONResponse:
        target_func = RpcRegistry.get(func_name)

        if target_func is None:
            raise HTTPException(status_code=404, detail=f"RPC function '{func_name}' not found")

        try:
            data = await request.json()
        except Exception:
            data = {}

        result = await target_func(**data)

        json_content = wtfui_json_dumps(result)

        return JSONResponse(
            content=json.loads(json_content),
            media_type="application/json",
        )

    @app.get("/app.mfbc")
    async def get_wtfuibyte() -> Response:
        from wtfui.web.compiler.wtfuibyte import compile_to_wtfuibyte

        demo_source = """
count = Signal(0)
def increment():
    count.value += 1

with Div():
    Text(f"Count: {count.value}")
    Button("Up", on_click=increment)
"""
        binary = compile_to_wtfuibyte(demo_source)

        return Response(
            content=binary,
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-cache, must-revalidate",
            },
        )

    @app.get("/app.fsm")
    async def get_sourcemap() -> Response:
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        demo_source = """
count = Signal(0)
def increment():
    count.value += 1

with Div():
    Text(f"Count: {count.value}")
    Button("Up", on_click=increment)
"""
        compiler = WtfUICompiler()
        _, _, fsm_bytes = compiler.compile_full(demo_source, filename="app.py")

        return Response(
            content=fsm_bytes,
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-cache, must-revalidate",
            },
        )

    return app


def run_app(
    root_component: Any,
    host: str = "127.0.0.1",
    port: int = 8000,
    renderer: Renderer | None = None,
) -> None:
    import uvicorn

    app = create_app(root_component, renderer=renderer)
    uvicorn.run(app, host=host, port=port)
