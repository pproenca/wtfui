import inspect
import json
import logging
import threading
import uuid
from contextvars import ContextVar
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

# Context variable for current session (React 19-style per-client isolation)
_current_session: ContextVar[SessionState | None] = ContextVar("current_session", default=None)

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

// Helper to find element by stable data-key attribute
function findByKey(key) {
    return document.querySelector(`[data-key="${key}"]`);
}

// Handle incoming patches from server
socket.onmessage = (event) => {
    const patch = JSON.parse(event.data);
    console.log('[wtfui] Received patch:', patch);

    // Preserve focus and selection state for inputs BEFORE any DOM changes
    const activeEl = document.activeElement;
    const wasInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');
    const selectionStart = wasInput ? activeEl.selectionStart : null;
    const selectionEnd = wasInput ? activeEl.selectionEnd : null;
    // Use data-key as stable identifier (doesn't change on re-render)
    const activeKey = wasInput ? activeEl.getAttribute('data-key') : null;

    switch (patch.op) {
        case 'update_prop':
            // Granular property update - no DOM replacement, focus preserved
            const propEl = findByKey(patch.target_key);
            if (propEl) {
                if (patch.value === null) {
                    propEl.removeAttribute(patch.prop_name);
                } else if (patch.prop_name === 'value') {
                    // Don't update value if this is the focused input (user is typing)
                    if (propEl !== activeEl) {
                        propEl.value = patch.value;
                    }
                } else if (patch.prop_name === 'content') {
                    propEl.textContent = patch.value;
                } else if (patch.prop_name === 'class') {
                    propEl.className = patch.value;
                } else {
                    propEl.setAttribute(patch.prop_name, patch.value);
                }
            }
            break;

        case 'create':
            // Insert new element
            const parentEl = findByKey(patch.parent_key) || document.getElementById('wtfui-root');
            if (parentEl && patch.html) {
                const temp = document.createElement('div');
                temp.innerHTML = patch.html;
                const newEl = temp.firstElementChild;
                if (patch.index >= parentEl.children.length) {
                    parentEl.appendChild(newEl);
                } else {
                    parentEl.insertBefore(newEl, parentEl.children[patch.index]);
                }
            }
            break;

        case 'delete':
            // Remove element
            const delEl = findByKey(patch.target_key);
            if (delEl) {
                delEl.remove();
            }
            break;

        case 'replace':
            // Replace element entirely (when key/tag changed)
            const oldEl = findByKey(patch.target_key);
            if (oldEl && patch.html) {
                oldEl.outerHTML = patch.html;
            } else if (patch.target_id) {
                // Fallback to id-based lookup
                const el = document.getElementById(patch.target_id);
                if (el) el.outerHTML = patch.html;
            }
            break;

        case 'update_root':
            // Full re-render (legacy fallback)
            const root = document.getElementById('wtfui-root');
            if (root) {
                root.innerHTML = patch.html;
            }
            break;
    }

    // Restore focus using stable data-key (doesn't change on re-render)
    if (activeKey) {
        const newInput = findByKey(activeKey);
        if (newInput && newInput !== document.activeElement) {
            newInput.focus();
            // Restore cursor position
            if (selectionStart !== null) {
                try {
                    newInput.setSelectionRange(selectionStart, selectionEnd);
                } catch (e) {
                    // Some input types don't support setSelectionRange
                }
            }
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


class SessionState:
    """Per-connection session state (React 19-style client isolation).

    Each WebSocket connection gets its own SessionState with isolated:
    - Signal values (via signal_values dict)
    - Element registry (handlers)
    - Root element tree
    - WebSocket connection (for broadcast)
    """

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.signal_values: dict[str, Any] = {}  # Signal name -> value
        self.registry: ElementRegistry = ElementRegistry()
        self.root_element: Any = None
        self.websocket: WebSocket | None = None  # For broadcast
        self._render_lock = threading.Lock()

    def get_signal(self, name: str, default: Any = None) -> Any:
        """Get a signal value for this session."""
        return self.signal_values.get(name, default)

    def set_signal(self, name: str, value: Any) -> None:
        """Set a signal value for this session."""
        self.signal_values[name] = value


def get_current_session() -> SessionState | None:
    """Get the current session from context (React 19-style)."""
    return _current_session.get()


def set_current_session(session: SessionState | None) -> None:
    """Set the current session in context."""
    _current_session.set(session)


class SessionManager:
    """Manages per-connection sessions (React 19-style)."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def create_session(self, websocket: WebSocket | None = None) -> SessionState:
        """Create a new session."""
        session = SessionState()
        session.websocket = websocket
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionState | None:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_all_sessions(self) -> list[SessionState]:
        """Get all active sessions (for broadcast)."""
        with self._lock:
            return list(self._sessions.values())

    def remove_session(self, session_id: str) -> None:
        """Remove a session."""
        with self._lock:
            self._sessions.pop(session_id, None)


class AppState:
    def __init__(self) -> None:
        self.root_component: Any = None
        self.root_element: Any = None
        self.registry: ElementRegistry = ElementRegistry()
        self.renderer = HTMLRenderer()
        self._render_lock = threading.Lock()
        self.session_manager = SessionManager()


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

        # React 19-style: Create isolated session for this WebSocket connection
        session = state.session_manager.create_session(websocket=websocket)
        logger.debug(f"Created session {session.session_id} for WebSocket connection")

        async def _session_render() -> Any:
            """Render root with session-specific state."""
            with session._render_lock:
                session.registry.clear()
                # Set current session context before rendering
                set_current_session(session)
                try:
                    session.root_element = await state.root_component()
                    session.registry.register_tree(session.root_element)
                finally:
                    set_current_session(None)
                return session.root_element

        async def _broadcast_to_others() -> None:
            """Broadcast update to all other connected sessions (real-time updates)."""
            for other_session in state.session_manager.get_all_sessions():
                if other_session.session_id == session.session_id:
                    continue  # Don't send to self
                if other_session.websocket is None:
                    continue

                try:
                    # Re-render for other session's context
                    set_current_session(other_session)
                    try:
                        other_session.registry.clear()
                        other_session.root_element = await state.root_component()
                        other_session.registry.register_tree(other_session.root_element)
                        html = state.renderer.render(other_session.root_element)
                    finally:
                        set_current_session(None)

                    await other_session.websocket.send_json({"op": "update_root", "html": html})
                except Exception:
                    logger.debug(f"Failed to broadcast to session {other_session.session_id}")

        try:
            # Initial render for this session
            root = await _session_render()
            html = state.renderer.render(root)
            await websocket.send_json({"op": "update_root", "html": html})

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

                # Set session context for handler execution
                set_current_session(session)
                try:
                    match event_type:
                        case "click":
                            handler = session.registry.get_handler(element_id, "click")
                            if handler:
                                if inspect.iscoroutinefunction(handler):
                                    await handler()
                                else:
                                    handler()

                                root = await _session_render()
                                html = state.renderer.render(root)
                                await websocket.send_json({"op": "update_root", "html": html})

                                # Broadcast to other clients for real-time updates
                                await _broadcast_to_others()

                        case "input":
                            # Live updates on every keystroke
                            element = session.registry.get(element_id)
                            value = data.get("value", "")

                            if element:
                                bind = getattr(element, "bind", None)
                                if bind is not None:
                                    bind.value = value

                            handler = session.registry.get_handler(element_id, "change")
                            if handler:
                                if inspect.iscoroutinefunction(handler):
                                    await handler(value)
                                else:
                                    handler(value)

                                root = await _session_render()
                                html = state.renderer.render(root)
                                await websocket.send_json({"op": "update_root", "html": html})

                        case "change":
                            element = session.registry.get(element_id)
                            value = data.get("value", "")

                            if element and hasattr(element, "_text_value"):
                                if getattr(element, "bind", None) is not None:
                                    element.bind.value = value
                                else:
                                    element._text_value = value

                            handler = session.registry.get_handler(element_id, "change")
                            if handler:
                                if inspect.iscoroutinefunction(handler):
                                    await handler(value)
                                else:
                                    handler(value)

                                root = await _session_render()
                                html = state.renderer.render(root)
                                await websocket.send_json({"op": "update_root", "html": html})

                        case "enter":
                            # Handle Enter key in input fields
                            handler = session.registry.get_handler(element_id, "enter")
                            if handler:
                                if inspect.iscoroutinefunction(handler):
                                    await handler()
                                else:
                                    handler()

                                root = await _session_render()
                                html = state.renderer.render(root)
                                await websocket.send_json({"op": "update_root", "html": html})

                                # Broadcast to other clients for real-time updates
                                await _broadcast_to_others()
                finally:
                    set_current_session(None)

        except Exception:
            logger.debug("WebSocket connection closed", exc_info=True)
        finally:
            # Cleanup session on disconnect
            state.session_manager.remove_session(session.session_id)
            logger.debug(f"Removed session {session.session_id}")

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
