# examples/chat/app.py
"""Chat App - Demonstrates full-stack @rpc and real-time updates.

This example showcases:
- @rpc decorator for server functions
- Client-server type safety via annotations
- WebSocket for real-time updates
- Async component patterns
- SessionSignal for per-user state (React 19-style isolation)

Run with: cd examples/chat && uv run wtfui dev --web
"""

from components import ChatBubble

from server import Message, get_history, send_message
from wtfui import Element, SessionSignal, Signal, component
from wtfui.core.style import Colors, Style
from wtfui.ui import Box, Button, Flex, Input, Text
from wtfui.web.server import create_app

# Shared state - all users see the same messages (correct for chat)
_messages: Signal[list[Message]] = Signal([])

# Per-user state (React 19-style: each session has isolated values)
_input_text: SessionSignal[str] = SessionSignal("", name="input_text")
_username: SessionSignal[str] = SessionSignal("", name="username")
_is_logged_in: SessionSignal[bool] = SessionSignal(False, name="is_logged_in")


async def load_messages() -> None:
    """Load message history from server."""
    history = await get_history()
    _messages.value = history


async def handle_send() -> None:
    """Send a message via RPC."""
    text = _input_text.value.strip()
    if not text or not _username.value:
        return

    # Call server function - this is an RPC call!
    message = await send_message(user=_username.value, text=text)

    # Update local state
    _messages.value = [*_messages.value, message]
    _input_text.value = ""


def handle_login() -> None:
    """Log in with username."""
    if _username.value.strip():
        _is_logged_in.value = True


@component
async def LoginScreen() -> Element:
    """Username entry screen with centered layout."""
    with Flex(
        direction="column",
        justify="center",
        align="center",
        height="100vh",
        gap=16,
        style=Style(bg=Colors.Slate._100),
    ) as screen:
        Text(
            "Welcome to Flow Chat",
            style=Style(font_size="2xl", font_weight="bold", color=Colors.Slate._800),
        )
        Text("Enter your username to get started", style=Style(color=Colors.Slate._500))
        with Flex(direction="row", gap=8):
            Input(bind=_username, placeholder="Username", width=200)
            Button(
                label="Join",
                on_click=handle_login,
                style=Style(bg=Colors.Blue._600, color="white"),
            )

    return screen


@component
async def ChatScreen() -> Element:
    """Main chat interface with flex layout."""
    await load_messages()

    with Flex(direction="column", height="100vh") as screen:
        # Header - fixed height
        with Box(padding=16, style=Style(bg=Colors.Blue._600)):
            Text(
                f"Flow Chat - {_username.value}",
                style=Style(font_size="xl", font_weight="bold", color="white"),
            )

        # Messages area - grows to fill, reverse column for newest at bottom
        with Flex(
            direction="column-reverse",
            flex_grow=1,
            padding=16,
            gap=8,
            style=Style(bg="white", overflow="auto"),
        ):
            for chat_message in reversed(_messages.value):
                await ChatBubble(
                    message=chat_message,
                    is_own=chat_message.user == _username.value,
                )

        # Input area - fixed at bottom
        with Box(
            padding=16,
            style=Style(border_top=True, border_color=Colors.Slate._200, bg="white"),
        ):
            with Flex(direction="row", gap=8, align="center"):
                Input(
                    bind=_input_text,
                    placeholder="Type a message...",
                    flex_grow=1,
                    on_enter=handle_send,  # Send on Enter key
                )
                Button(
                    label="Send",
                    on_click=handle_send,
                    style=Style(bg=Colors.Blue._600, color="white", px=4, py=2, rounded="md"),
                )

    return screen


@component
async def ChatApp() -> Element:
    """Root component with login/chat routing."""
    if _is_logged_in.value:
        return await ChatScreen()
    else:
        return await LoginScreen()


# Create and run server
app = create_app(ChatApp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
