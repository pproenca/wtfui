"""Tests for chat RPC functions."""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.mark.asyncio
async def test_send_message() -> None:
    from examples.chat.server.rpc import Message, clear_messages, send_message

    clear_messages()
    msg = await send_message(user="Alice", text="Hello!")

    assert isinstance(msg, Message)
    assert msg.user == "Alice"
    assert msg.text == "Hello!"
    assert isinstance(msg.timestamp, datetime)


@pytest.mark.asyncio
async def test_get_history() -> None:
    from examples.chat.server.rpc import clear_messages, get_history, send_message

    clear_messages()
    await send_message(user="Alice", text="First")
    await send_message(user="Bob", text="Second")

    history = await get_history()

    assert len(history) == 2
    assert history[0].text == "First"
    assert history[1].text == "Second"


@pytest.mark.asyncio
async def test_get_history_limit() -> None:
    from examples.chat.server.rpc import clear_messages, get_history, send_message

    clear_messages()
    for i in range(10):
        await send_message(user="User", text=f"Message {i}")

    history = await get_history(limit=5)

    assert len(history) == 5
    # Should return last 5 messages
    assert history[0].text == "Message 5"


@pytest.mark.asyncio
async def test_get_online_users() -> None:
    from examples.chat.server.rpc import (
        clear_messages,
        get_online_users,
        send_message,
    )

    clear_messages()
    await send_message(user="Alice", text="Hi")
    await send_message(user="Bob", text="Hello")
    await send_message(user="Alice", text="How are you?")

    users = await get_online_users()

    assert sorted(users) == ["Alice", "Bob"]
