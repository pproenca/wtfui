from collections.abc import Callable  # noqa: TC003 - Required at runtime for PEP 649
from typing import Any

from wtfui.tui.runtime import TUIRuntime


def run_tui(
    app: Callable[[], Any],
    *,
    fps: int = 12,
    mouse: bool = True,
    on_key: Callable[[str], None] | None = None,
    inline: bool = False,
) -> None:
    runtime = TUIRuntime(app, fps=fps, mouse=mouse, on_key=on_key, inline=inline)
    runtime.start()
