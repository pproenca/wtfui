"""Tests for chat RPC functions."""

import asyncio
from datetime import datetime

import pytest


@pytest.mark.asyncio
async def test_send_message() -> None:
    from server.rpc import Message, clear_messages, send_message

    clear_messages()
    msg = await send_message(user="Alice", text="Hello!")

    assert isinstance(msg, Message)
    assert msg.user == "Alice"
    assert msg.text == "Hello!"
    assert isinstance(msg.timestamp, datetime)


@pytest.mark.asyncio
async def test_get_history() -> None:
    from server.rpc import clear_messages, get_history, send_message

    clear_messages()
    await send_message(user="Alice", text="First")
    await send_message(user="Bob", text="Second")

    history = await get_history()

    assert len(history) == 2
    assert history[0].text == "First"
    assert history[1].text == "Second"


@pytest.mark.asyncio
async def test_get_history_limit() -> None:
    from server.rpc import clear_messages, get_history, send_message

    clear_messages()
    for i in range(10):
        await send_message(user="User", text=f"Message {i}")

    history = await get_history(limit=5)

    assert len(history) == 5
    # Should return last 5 messages
    assert history[0].text == "Message 5"


@pytest.mark.asyncio
async def test_get_online_users() -> None:
    from server.rpc import (
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


@pytest.mark.asyncio
async def test_send_message_rejects_empty_text() -> None:
    """Verify send_message rejects empty message text."""
    from server.rpc import clear_messages, send_message

    clear_messages()

    with pytest.raises(ValueError, match="Message text cannot be empty"):
        await send_message(user="Alice", text="   ")


@pytest.mark.asyncio
async def test_send_message_rejects_empty_username() -> None:
    """Verify send_message rejects empty username."""
    from server.rpc import clear_messages, send_message

    clear_messages()

    with pytest.raises(ValueError, match="Username cannot be empty"):
        await send_message(user="", text="Hello")


@pytest.mark.asyncio
async def test_send_message_rejects_long_text() -> None:
    """Verify send_message rejects messages over 2000 characters."""
    from server.rpc import clear_messages, send_message

    clear_messages()

    with pytest.raises(ValueError, match="Message text too long"):
        await send_message(user="Alice", text="x" * 2001)


@pytest.mark.asyncio
async def test_concurrent_message_sending() -> None:
    """Verify messages can be sent concurrently without data corruption."""
    from server.rpc import clear_messages, get_history, send_message

    clear_messages()

    # Send 100 messages concurrently
    tasks = [send_message(user=f"User{i}", text=f"Message {i}") for i in range(100)]
    await asyncio.gather(*tasks)

    history = await get_history(limit=100)

    # All messages should be preserved
    assert len(history) == 100
