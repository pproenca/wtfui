# src/flow/server/app.py
"""FastAPI application factory for Flow apps (Renderer Protocol)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse

from flow.renderer import HTMLRenderer, Renderer
from flow.server.session import LiveSession


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
    _renderer = renderer or HTMLRenderer()

    # Store sessions by connection
    sessions: dict[str, LiveSession] = {}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Serve the initial HTML page."""
        # Render the component using Renderer Protocol
        root = await root_component()
        full_html = _renderer.render(root)  # Not hardcoded to_html!

        html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flow App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="flow-root">{full_html}</div>
    <script>
        const socket = new WebSocket(`ws://${{location.host}}/ws`);
        socket.onmessage = (event) => {{
            const patch = JSON.parse(event.data);
            if (patch.op === 'replace') {{
                const el = document.getElementById(patch.target_id);
                if (el) el.outerHTML = patch.html;
            }}
        }};

        document.addEventListener('click', (e) => {{
            const id = e.target.id;
            if (id && id.startsWith('flow-')) {{
                socket.send(JSON.stringify({{
                    type: 'click',
                    target_id: id
                }}));
            }}
        }});
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html_doc)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle WebSocket connections for live updates."""
        await websocket.accept()

        # Render component for this session (with shared renderer)
        root = await root_component()
        session = LiveSession(root, websocket, renderer=_renderer)

        session_id = str(id(websocket))
        sessions[session_id] = session

        try:
            # Keep connection alive and handle events
            while True:
                data = await websocket.receive_json()
                await session._handle_event(data)
        except Exception:  # noqa: S110 - WebSocket disconnect is expected
            pass  # Connection closed, cleanup in finally
        finally:
            sessions.pop(session_id, None)

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
