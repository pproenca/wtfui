# examples/chat/server/rpc.py
"""Server-side RPC functions for chat."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from flow.rpc import rpc

# In-memory message store (would be database in production)
_messages: list[Message] = []


@dataclass
class Message:
    """A chat message."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user: str = ""
    text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


def clear_messages() -> None:
    """Clear all messages (for testing)."""
    _messages.clear()


@rpc
async def send_message(user: str, text: str) -> Message:
    """Send a new message.

    This function runs on the server. The client receives a fetch stub.
    Type annotations define the API contract.
    """
    msg = Message(user=user, text=text)
    _messages.append(msg)
    # In a full implementation, this would broadcast via WebSocket
    return msg


@rpc
async def get_history(limit: int = 50) -> list[Message]:
    """Get recent message history.

    Args:
        limit: Maximum messages to return
    """
    return _messages[-limit:]


@rpc
async def get_online_users() -> list[str]:
    """Get list of online users.

    In production, this would track WebSocket connections.
    """
    # For demo, return unique users from recent messages
    users = {msg.user for msg in _messages[-20:]}
    return sorted(users)
