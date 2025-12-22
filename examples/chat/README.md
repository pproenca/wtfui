# Chat App

A real-time chat application demonstrating @rpc server functions.

## Run

```bash
uv run wtfui dev --web
# Open http://localhost:8002
```

## Patterns Demonstrated

| Pattern | Usage |
|---------|-------|
| **@rpc decorator** | Server functions with client stubs |
| **Type safety** | Annotations enforced across client/server |
| **Async components** | `async def ChatScreen()` with await |
| **Conditional rendering** | Login/Chat screen routing via Signal |
| **Input binding** | Two-way binding with Signal state |

## Key Files

- `app.py` - Main ChatApp with login/chat screens
- `server/rpc.py` - Server-side RPC functions
- `components/chat_bubble.py` - ChatBubble component

## Code Highlights

```python
# Server-side function (body stays on server)
@rpc
async def send_message(user: str, text: str) -> Message:
    return message_store.add(user, text)

# Client calls it like a normal function
message = await send_message(user=_username.value, text=text)

# Conditional routing with Signal
@component
async def ChatApp() -> Element:
    if _is_logged_in.value:
        return await ChatScreen()
    else:
        return await LoginScreen()
```

## RPC Security

The `@rpc` decorator uses AST transformation:
- **Server**: Keeps the full function body
- **Client**: Gets a fetch stub that calls `/api/rpc/{func_name}`

Server-only imports (like `sqlalchemy`, `os`) stay server-side.
