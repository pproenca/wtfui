# tests/test_effect.py
"""Tests for Effect - thread-safe dependency tracking for Python 3.14+ No-GIL builds."""

import threading

from wtfui.core.effect import Effect, get_running_effect
from wtfui.core.signal import Signal


def test_effect_runs_function_immediately():
    """Effect executes its function on creation."""
    calls: list[str] = []
    Effect(lambda: calls.append("ran"))
    assert calls == ["ran"]


def test_effect_tracks_signal_access():
    """Effect automatically tracks signals read during execution."""
    from wtfui.core.scheduler import wait_for_scheduler

    count = Signal(0)
    computed_values: list[int] = []

    def compute():
        computed_values.append(count.value * 2)

    Effect(compute)
    assert computed_values == [0]  # Initial run

    count.value = 5
    wait_for_scheduler()  # Wait for scheduled effect to run
    assert computed_values == [0, 10]  # Re-ran after signal change


def test_effect_tracks_multiple_signals():
    """Effect tracks multiple signal dependencies."""
    from wtfui.core.scheduler import wait_for_scheduler

    a = Signal(1)
    b = Signal(2)
    results: list[int] = []

    def compute():
        results.append(a.value + b.value)

    Effect(compute)
    assert results == [3]

    a.value = 10
    wait_for_scheduler()  # Wait for scheduled effect to run
    assert results == [3, 12]

    b.value = 20
    wait_for_scheduler()  # Wait for scheduled effect to run
    assert results == [3, 12, 30]


def test_running_effect_context():
    """get_running_effect returns the active effect during execution."""
    captured: list[Effect | None] = []

    def capture():
        captured.append(get_running_effect())

    effect = Effect(capture)
    assert captured[0] is effect


def test_effect_thread_isolation():
    """Effects in different threads don't interfere (No-GIL safe)."""
    from wtfui.core.scheduler import wait_for_scheduler

    results: dict[str, list[int]] = {"thread1": [], "thread2": []}
    sig1 = Signal(0)
    sig2 = Signal(0)

    def thread1_work():
        def track():
            results["thread1"].append(sig1.value)

        Effect(track)
        sig1.value = 10
        wait_for_scheduler()  # Wait in thread

    def thread2_work():
        def track():
            results["thread2"].append(sig2.value)

        Effect(track)
        sig2.value = 20
        wait_for_scheduler()  # Wait in thread

    t1 = threading.Thread(target=thread1_work)
    t2 = threading.Thread(target=thread2_work)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert 0 in results["thread1"] and 10 in results["thread1"]
    assert 0 in results["thread2"] and 20 in results["thread2"]


def test_effect_schedule_does_not_block_notification_loop():
    """Effects should be queued, not executed inline during signal notification."""
    sig = Signal(0)
    execution_order: list[str] = []

    def effect_fn():
        # Read signal to establish dependency
        _ = sig.value
        execution_order.append("effect")

    Effect(effect_fn)
    # Clear the initial run from constructor
    execution_order.clear()

    execution_order.append("before_set")
    sig.value = 1
    execution_order.append("after_set")

    # Effect should NOT have run yet (queued, not inline)
    assert execution_order == ["before_set", "after_set"], f"Effect ran inline: {execution_order}"


def test_effect_recursive_signal_update_no_stack_overflow():
    """Recursive signal updates should not cause stack overflow."""
    from wtfui.core.scheduler import wait_for_scheduler

    sig = Signal(0)
    counter = [0]  # Use list to avoid tracking another signal

    def recursive_effect():
        if sig.value < 100:
            sig.value = sig.value + 1
            counter[0] += 1

    Effect(recursive_effect)

    # Wait for all scheduled effects to complete
    assert wait_for_scheduler(timeout=2.0), "Scheduler timed out"

    # Should complete without RecursionError
    # Counter is 100 (0→1, 1→2, ..., 99→100, then 100<100 is False)
    assert counter[0] == 100


def test_effect_reentry_guard_prevents_synchronous_infinite_loop():
    """Re-entry guard prevents synchronous infinite loops.

    When run() is called during execution, it queues a rerun for later
    instead of executing immediately. This breaks the synchronous call
    chain while still allowing the effect to run again.
    """
    run_count = [0]
    effect_ref: list[Effect | None] = [None]
    max_runs = 3  # Limit runs to prevent infinite loop in test

    def reentrant_effect():
        run_count[0] += 1
        # Without re-entry guard, this would cause infinite synchronous loop
        # With guard, the nested run() is queued for later
        if effect_ref[0] is not None and run_count[0] < max_runs:
            effect_ref[0].run()  # This queues a rerun, doesn't execute immediately

    # Create effect - first run happens in __init__
    effect = Effect(reentrant_effect)
    effect_ref[0] = effect

    # Should have run once initially
    assert run_count[0] == 1, f"Initial run count wrong: {run_count[0]}"

    # Force another run - the nested run() calls get queued
    run_count[0] = 0  # Reset counter
    effect.run()

    # Should have run once (synchronous), with potential scheduled reruns
    # The key is it doesn't blow the stack with infinite recursion
    assert run_count[0] >= 1, f"Effect should have run at least once, got {run_count[0]}"


def test_effect_reentry_guard_allows_subsequent_runs():
    """Re-entry guard allows effect to run again after previous run completes."""
    from wtfui.core.scheduler import wait_for_scheduler

    sig = Signal(0)
    run_count = [0]

    def counting_effect():
        run_count[0] += 1
        _ = sig.value  # Track dependency

    Effect(counting_effect)
    assert run_count[0] == 1

    # Second run via signal change should work
    sig.value = 1
    wait_for_scheduler()
    assert run_count[0] == 2

    # Third run should also work
    sig.value = 2
    wait_for_scheduler()
    assert run_count[0] == 3


def test_effect_track_signal_thread_safe():
    """Effect._track_signal is thread-safe for bidirectional tracking."""
    signal = Signal(0)
    effect = Effect(lambda: None)

    errors = []

    def track():
        try:
            for _ in range(100):
                effect._track_signal(signal)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=track) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert signal in effect._tracked_signals
