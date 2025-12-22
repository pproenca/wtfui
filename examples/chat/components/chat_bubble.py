# examples/chat/components/chat_bubble.py
"""ChatBubble component for displaying messages."""

from wtfui import Element, component
from wtfui.core.style import Colors, Style
from wtfui.ui import Box, Flex, Text
from wtfui.ui.layout import JustifyLiteral  # noqa: TC001 - needed at runtime for @component

from ..server.rpc import Message  # noqa: TC001 - needed at runtime for @component


@component
async def ChatBubble(message: Message, is_own: bool = False) -> Element:
    """A single chat message bubble.

    Args:
        message: The message to display
        is_own: Whether this is the current user's message
    """
    alignment: JustifyLiteral = "flex-end" if is_own else "flex-start"
    bubble_style = (
        Style(bg=Colors.Blue._500, color="white", rounded="lg")
        if is_own
        else Style(bg=Colors.Slate._200, rounded="lg")
    )

    with Flex(direction="row", justify=alignment, width="100%") as bubble:
        with Box(
            padding=12,
            max_width="70%",
            style=bubble_style,
        ):
            if not is_own:
                Text(
                    message.user,
                    style=Style(font_size="xs", font_weight="bold", mb=1),
                )
            Text(message.text)
            Text(
                message.timestamp.strftime("%H:%M"),
                style=Style(font_size="xs", opacity=0.7, mt=1),
            )

    return bubble
