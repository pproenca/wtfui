import sys
from functools import wraps
from typing import Any, ClassVar

IS_SERVER = not (sys.platform == "emscripten" or sys.platform == "wasi")


class RpcRegistry:
    routes: ClassVar[dict[str, Any]] = {}

    @classmethod
    def clear(cls) -> None:
        cls.routes = {}

    @classmethod
    def get(cls, name: str) -> Any | None:
        return cls.routes.get(name)


def rpc(func: Any) -> Any:
    if IS_SERVER:
        RpcRegistry.routes[func.__name__] = func

        @wraps(func)
        async def server_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return server_wrapper
    else:
        return func
