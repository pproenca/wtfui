# examples/chat/app.py
"""Chat App - Demonstrates full-stack @rpc and real-time updates.

This example showcases:
- @rpc decorator for server functions
- Client-server type safety via annotations
- WebSocket for real-time updates
- Async component patterns

Run with: uv run python examples/chat/app.py
"""

from __future__ import annotations

from flow import Element, Signal, component
from flow.server import create_app
from flow.ui import Box, Button, Flex, Input, Text

from .components import ChatBubble
from .server import Message, get_history, send_message

# Client state
messages: Signal[list[Message]] = Signal([])
input_text: Signal[str] = Signal("")
username: Signal[str] = Signal("")
is_logged_in: Signal[bool] = Signal(False)


async def load_messages() -> None:
    """Load message history from server."""
    history = await get_history()
    messages.value = history


async def handle_send() -> None:
    """Send a message via RPC."""
    text = input_text.value.strip()
    if not text or not username.value:
        return

    # Call server function - this is an RPC call!
    msg = await send_message(user=username.value, text=text)

    # Update local state
    messages.value = [*messages.value, msg]
    input_text.value = ""


def handle_login() -> None:
    """Log in with username."""
    if username.value.strip():
        is_logged_in.value = True


@component
async def LoginScreen() -> Element:
    """Username entry screen."""
    with Flex(
        direction="column",
        justify="center",
        align="center",
        height="100vh",
        gap=16,
        cls="bg-gray-100",
    ) as screen:
        with Text("Welcome to Flow Chat", cls="text-2xl font-bold"):
            pass
        with Text("Enter your username to get started", cls="text-gray-500"):
            pass
        with Flex(direction="row", gap=8):
            with Input(bind=username, placeholder="Username"):
                pass
            with Button(label="Join", on_click=handle_login):
                pass

    return screen


@component
async def ChatScreen() -> Element:
    """Main chat interface."""
    # Load history on mount
    await load_messages()

    with Flex(direction="column", height="100vh") as screen:
        # Header
        with (
            Box(padding=16, cls="bg-blue-600 text-white"),
            Text(f"Flow Chat - {username.value}", cls="text-xl font-semibold"),
        ):
            pass

        # Messages area - grows to fill space, scrolls
        with Flex(
            direction="column-reverse",
            flex_grow=1,
            padding=16,
            gap=8,
            cls="overflow-y-auto bg-white",
        ):
            # Reverse so newest at bottom
            for msg in reversed(messages.value):
                await ChatBubble(
                    message=msg,
                    is_own=msg.user == username.value,
                )

        # Input area - fixed at bottom
        with Box(padding=16, cls="border-t bg-white"), Flex(direction="row", gap=8):
            with Input(
                bind=input_text,
                placeholder="Type a message...",
                flex_grow=1,
            ):
                pass
            with Button(label="Send", on_click=handle_send):
                pass

    return screen


@component
async def ChatApp() -> Element:
    """Root component with login/chat routing."""
    if is_logged_in.value:
        return await ChatScreen()
    else:
        return await LoginScreen()


# Create and run server
app = create_app(ChatApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
