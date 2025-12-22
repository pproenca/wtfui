#!/usr/bin/env python3
"""LLM Chat demo demonstrating inline TUI with focus system.

This example shows the "Claude Code" experience:
- Inline rendering (no alt screen)
- Focus-based text input
- Dynamic height based on content
- Clean artifact left after exit

Usage:
    python examples/console/llm_chat.py
"""

from wtfui import Signal, component
from wtfui.tui.renderer import run_tui
from wtfui.ui import HStack, Input, Text, VStack


@component
def Message(role: str, content: str):
    """A single chat message."""
    prefix = "You: " if role == "user" else "AI: "

    with HStack():
        Text(f"{prefix}{content}")


@component
def LLMChat():
    """Interactive LLM chat interface."""
    messages: list[tuple[str, str]] = []
    messages_signal = Signal(messages)
    input_text = Signal("")

    def on_submit():
        text = input_text.value.strip()
        if text:
            # Add user message
            new_messages = list(messages_signal.value)
            new_messages.append(("user", text))
            # Simulate AI response
            new_messages.append(("ai", f"You said: {text}"))
            messages_signal.value = new_messages
            input_text.value = ""

    def on_key(key: str):
        if key == "enter":
            on_submit()

    with VStack(gap=1):
        Text("LLM Chat Demo (Enter to send, q to quit)")
        Text("-" * 40)

        # Message list
        with VStack(gap=0):
            for role, content in messages_signal.value:
                Message(role=role, content=content)

        Text("-" * 40)

        # Input area
        with HStack(gap=1):
            Text("> ")
            Input(bind=input_text, placeholder="Type a message...")

    return on_key


if __name__ == "__main__":
    run_tui(LLMChat, inline=True, mouse=True)
