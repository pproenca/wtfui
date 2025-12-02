# Chat App Tutorial

Build a real-time chat application demonstrating Flow's full-stack capabilities.

## Concepts Covered

1. **@rpc Decorator** - Server functions callable from client
2. **Type-Safe API** - Annotations define the contract
3. **WebSocket Updates** - Real-time message delivery
4. **Async Components** - Server-side data fetching

## Running the App

```bash
cd examples/chat
uv run python app.py
```

Open http://localhost:8002 in your browser.

## Code Walkthrough

### The @rpc Decorator

```python
from flow.rpc import rpc

@rpc
async def send_message(user: str, text: str) -> Message:
    """This runs on the SERVER."""
    msg = Message(user=user, text=text)
    await broadcast(msg)
    return msg
```

**What happens:**
1. On server: Function is registered and callable
2. On client: Function is replaced with fetch stub
3. Type annotations define the API contract

### Calling RPC from Client

```python
# This looks like a local call...
msg = await send_message(user="Alice", text="Hello!")

# ...but it's actually:
# POST /api/rpc/send_message {"user": "Alice", "text": "Hello!"}
```

**Security:** Server code is AST-stripped from client bundles. The client never sees the implementation.

### Async Component Pattern

```python
@component
async def ChatScreen():
    # Fetch data before rendering
    await load_messages()

    with Flex(...) as screen:
        for msg in messages.value:
            await ChatBubble(msg)

    return screen
```

Components can `await` RPC calls during render. Flow handles hydration automatically.

### Real-Time with WebSocket

```python
# Server broadcasts to all connected clients
async def broadcast(msg: Message):
    for session in active_sessions:
        await session.send(msg)

# Client receives and updates state
ws.on("message", lambda msg:
    messages.value.append(msg)
)
```

Flow's server manages WebSocket connections automatically. Signal updates are pushed to clients.

## Architecture

```
+-------------------------------------+
|           Client (Browser)          |
|  +-----------------------------+    |
|  |   ChatApp Component         |    |
|  |   - messages: Signal        |    |
|  |   - send_message() stub     |    |
|  +-----------------------------+    |
+----------------+--------------------+
                 | HTTP/WebSocket
+----------------v--------------------+
|           Server (Python)           |
|  +-----------------------------+    |
|  |   @rpc send_message()       |    |
|  |   @rpc get_history()        |    |
|  |   WebSocket broadcast       |    |
|  +-----------------------------+    |
+-------------------------------------+
```

## Try It Yourself

1. **Add typing indicator** - Show when others are typing
2. **Add message reactions** - Emoji reactions on messages
3. **Add rooms** - Multiple chat rooms with routing

## Framework Comparison

| Traditional | Flow |
|-------------|------|
| REST API + Frontend | Single Python codebase |
| OpenAPI/GraphQL schema | Type annotations |
| Separate client state | Shared Signal definitions |
| Manual WebSocket code | Automatic via @rpc |
