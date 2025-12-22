# examples/chat/server/rpc.py
"""Server-side RPC functions for chat."""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from wtfui.web.rpc import rpc

# Validation constants
MAX_MESSAGE_LENGTH = 2000
MAX_USERNAME_LENGTH = 50


@dataclass
class Message:
    """A chat message."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user: str = ""
    text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MessageStore:
    """Thread-safe in-memory message store.

    Encapsulates message storage with proper locking.
    In production, this would be backed by a database.
    """

    _messages: list[Message] = field(default_factory=list)
    _messages_lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, message: Message) -> None:
        """Add a message to the store."""
        with self._messages_lock:
            self._messages.append(message)

    def get_recent(self, limit: int = 50) -> list[Message]:
        """Get recent messages."""
        with self._messages_lock:
            return list(self._messages[-limit:])

    def get_recent_users(self, limit: int = 20) -> list[str]:
        """Get unique users from recent messages."""
        with self._messages_lock:
            users = {msg.user for msg in self._messages[-limit:]}
        return sorted(users)

    def clear(self) -> None:
        """Clear all messages (for testing)."""
        with self._messages_lock:
            self._messages.clear()


# Default store instance (can be replaced for testing)
_store = MessageStore()


def get_store() -> MessageStore:
    """Get the message store instance."""
    return _store


def clear_messages() -> None:
    """Clear all messages (for testing)."""
    _store.clear()


@rpc
async def send_message(user: str, text: str) -> Message:
    """Send a new message.

    This function runs on the server. The client receives a fetch stub.
    Type annotations define the API contract.

    Raises:
        ValueError: If user or text is empty/invalid
    """
    # Validate inputs
    user = user.strip()
    text = text.strip()

    if not user:
        raise ValueError("Username cannot be empty")
    if len(user) > MAX_USERNAME_LENGTH:
        raise ValueError(f"Username too long (max {MAX_USERNAME_LENGTH} chars)")
    if not text:
        raise ValueError("Message text cannot be empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message text too long (max {MAX_MESSAGE_LENGTH} chars)")

    message = Message(user=user, text=text)
    _store.add(message)
    # In a full implementation, this would broadcast via WebSocket
    return message


@rpc
async def get_history(limit: int = 50) -> list[Message]:
    """Get recent message history.

    Args:
        limit: Maximum messages to return
    """
    return _store.get_recent(limit)


@rpc
async def get_online_users() -> list[str]:
    """Get list of online users.

    In production, this would track WebSocket connections.
    """
    # For demo, return unique users from recent messages
    return _store.get_recent_users()
