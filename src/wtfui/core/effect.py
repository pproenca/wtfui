import threading
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


_running_effect: ContextVar[Effect | None] = ContextVar("running_effect", default=None)


def get_running_effect() -> Effect | None:
    return _running_effect.get()


class Effect:
    __slots__ = (
        "__weakref__",
        "_is_running",
        "_lock",
        "_pending_rerun",
        "_scheduled",
        "_tracked_signals",
        "fn",
    )

    def __init__(self, fn: Callable[[], None]) -> None:
        self.fn = fn
        self._lock = threading.Lock()
        self._scheduled = False
        self._is_running = False
        self._pending_rerun = False
        self._tracked_signals = set()
        self.run()

    def schedule(self) -> None:
        from wtfui.core.scheduler import schedule_effect

        with self._lock:
            if self._scheduled:
                return
            self._scheduled = True

        schedule_effect(self)

    def run(self) -> None:
        with self._lock:
            self._scheduled = False

            if self._is_running:
                self._pending_rerun = True
                return
            self._is_running = True
            self._pending_rerun = False

        token = _running_effect.set(self)
        try:
            self.fn()
        finally:
            _running_effect.reset(token)

        should_rerun = False
        with self._lock:
            self._is_running = False
            if self._pending_rerun:
                self._pending_rerun = False
                should_rerun = True

        if should_rerun:
            self.schedule()

    def _track_signal(self, signal: Any) -> None:
        with self._lock:
            self._tracked_signals.add(signal)

    def dispose(self) -> None:
        from wtfui.core.signal import Signal

        for sig in list(self._tracked_signals):
            if isinstance(sig, Signal):
                sig._remove_effect(self)
        self._tracked_signals.clear()

    def __repr__(self) -> str:
        fn_name = getattr(self.fn, "__name__", "<anonymous>")
        return f"Effect({fn_name})"
