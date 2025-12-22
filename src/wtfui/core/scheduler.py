import threading
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.core.effect import Effect

_scheduler_lock = threading.Lock()
_pending_effects: deque[Effect] = deque()
_scheduler_condition = threading.Condition(_scheduler_lock)
_worker_thread: threading.Thread | None = None
_is_shutdown = False
_idle_event = threading.Event()
_idle_event.set()


def schedule_effect(effect: Effect) -> None:
    global _worker_thread, _is_shutdown
    with _scheduler_condition:
        _is_shutdown = False
        _pending_effects.append(effect)
        _idle_event.clear()

        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
            _worker_thread.start()
        _scheduler_condition.notify()


def _worker_loop() -> None:
    global _is_shutdown
    while True:
        with _scheduler_condition:
            while not _pending_effects and not _is_shutdown:
                _idle_event.set()
                _scheduler_condition.wait()
                _idle_event.clear()

            if _is_shutdown and not _pending_effects:
                return

            effect = _pending_effects.popleft()

        try:
            effect.run()
        except Exception:
            import traceback

            traceback.print_exc()


def wait_for_scheduler(timeout: float = 1.0) -> bool:
    return _idle_event.wait(timeout)


def reset_scheduler() -> None:
    global _is_shutdown
    with _scheduler_condition:
        _pending_effects.clear()
        _is_shutdown = False
        _idle_event.set()
