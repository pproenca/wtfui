# examples/chat/components/chat_bubble.py
"""ChatBubble component for displaying messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flow import Element, component
from flow.ui import Box, Flex, Text

if TYPE_CHECKING:
    from ..server.rpc import Message


@component
async def ChatBubble(message: Message, is_own: bool = False) -> Element:
    """A single chat message bubble.

    Args:
        message: The message to display
        is_own: Whether this is the current user's message
    """
    alignment = "flex-end" if is_own else "flex-start"
    bg_color = "bg-blue-500 text-white" if is_own else "bg-gray-200"

    with (
        Flex(direction="row", justify=alignment, width="100%") as bubble,
        Box(
            padding=12,
            max_width="70%",
            cls=f"rounded-lg {bg_color}",
        ),
    ):
        if not is_own:
            with Text(message.user, cls="text-xs font-semibold mb-1"):
                pass
        with Text(message.text):
            pass
        with Text(
            message.timestamp.strftime("%H:%M"),
            cls="text-xs opacity-70 mt-1",
        ):
            pass

    return bubble
