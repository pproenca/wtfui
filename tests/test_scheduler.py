import threading
import time

from wtfui.core.effect import Effect
from wtfui.core.scheduler import schedule_effect, wait_for_scheduler
from wtfui.core.signal import Signal


def test_scheduler_single_worker_thread():
    """Scheduler uses single persistent worker, not multiple Timer threads."""
    threads_seen: set[int] = set()

    # Use Signal to trigger effects asynchronously (not during Effect.__init__)
    trigger = Signal(0)

    def track_thread():
        # Read the signal to register dependency
        _ = trigger.value
        ident = threading.current_thread().ident
        if ident is not None:
            threads_seen.add(ident)

    # Create effects that depend on the signal
    # These will run once immediately on MainThread during __init__
    # We keep them in a list to prevent garbage collection
    _effects = [Effect(track_thread) for _ in range(10)]

    # Clear the threads_seen to only track scheduled runs
    threads_seen.clear()

    # Now trigger re-runs via signal change
    # This will schedule all effects on the worker thread
    trigger.value = 1

    wait_for_scheduler(timeout=1.0)
    # All scheduled runs should use the same worker thread
    assert len(threads_seen) == 1
    assert _effects  # Keep effects alive


def test_scheduler_waits_for_execution():
    """wait_for_scheduler blocks until effect runs, not just when popped."""
    flag = False

    def slow_effect():
        nonlocal flag
        time.sleep(0.1)  # Simulate work
        flag = True

    schedule_effect(Effect(slow_effect))

    # If scheduler signals idle too early (e.g. on pop), this will fail
    wait_for_scheduler(timeout=1.0)
    assert flag is True
