# tests/test_computed.py
"""Tests for Computed - memoized values that auto-update on signal changes."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from wtfui.core.computed import Computed
from wtfui.core.signal import Signal


def test_computed_returns_value():
    """Computed property returns calculated value."""
    a = Signal(2)
    b = Signal(3)

    @Computed
    def sum_ab():
        return a.value + b.value

    assert sum_ab() == 5


def test_computed_caches_result():
    """Computed caches until dependencies change."""
    call_count = 0
    a = Signal(10)

    @Computed
    def expensive():
        nonlocal call_count
        call_count += 1
        return a.value * 2

    # First call computes
    result1 = expensive()
    assert result1 == 20
    assert call_count == 1

    # Second call uses cache
    result2 = expensive()
    assert result2 == 20
    assert call_count == 1  # Not recomputed


def test_computed_invalidates_on_signal_change():
    """Computed re-calculates when signal changes."""
    x = Signal(5)

    @Computed
    def doubled():
        return x.value * 2

    assert doubled() == 10

    x.value = 7
    assert doubled() == 14


def test_computed_tracks_multiple_signals():
    """Computed tracks all signals accessed."""
    a = Signal(1)
    b = Signal(2)
    c = Signal(3)

    @Computed
    def total():
        return a.value + b.value + c.value

    assert total() == 6

    b.value = 10
    assert total() == 14

    c.value = 20
    assert total() == 31


def test_computed_thread_safety():
    """Computed must be thread-safe under concurrent access."""
    call_count = 0
    lock = threading.Lock()
    signal = Signal(0)

    @Computed
    def expensive():
        nonlocal call_count
        with lock:
            call_count += 1
        # Simulate work that could expose race conditions
        return signal.value * 2

    # Hammer the computed from multiple threads
    def access_computed(_: int) -> int:
        result: int = expensive()
        return result

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(access_computed, range(100)))

    # All results should be identical (0 * 2 = 0)
    assert all(r == 0 for r in results), f"Race condition: got different results {set(results)}"

    # Should only compute once (memoization works across threads)
    # Allow small variance due to initial parallel access
    assert call_count <= 8, f"Excessive recomputation: {call_count} calls (expected ≤8)"


def test_computed_allows_parallel_evaluation():
    """Multiple threads should be able to evaluate different computeds concurrently.

    Uses barrier synchronization to prove both computeds run in parallel.
    If execution were sequential, the second thread couldn't reach the barrier
    while the first thread waits at it.
    """
    sig = Signal(0)
    barrier = threading.Barrier(2)
    entered = {"a": False, "b": False}
    lock = threading.Lock()

    def compute_a():
        with lock:
            entered["a"] = True
        barrier.wait()
        return sig.value + 1

    def compute_b():
        with lock:
            entered["b"] = True
        barrier.wait()
        return sig.value + 2

    computed_a = Computed(compute_a)
    computed_b = Computed(compute_b)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(computed_a)
        future_b = executor.submit(computed_b)
        result_a = future_a.result(timeout=2.0)
        result_b = future_b.result(timeout=2.0)

    assert result_a == 1
    assert result_b == 2
    assert entered["a"] and entered["b"], "Both computeds should have executed"


def test_computed_lock_not_held_during_user_function():
    """The lock should be released during user function execution to allow parallelism.

    Tests that accessing a cached computed doesn't block while another computed
    is actively computing. Uses events for deterministic synchronization.
    """
    sig_a = Signal(0)
    sig_b = Signal(1)

    computing_b = threading.Event()
    read_a_done = threading.Event()
    results: dict[str, int | None] = {"a": None, "b": None}

    def compute_a():
        return sig_a.value + 1

    def compute_b():
        computing_b.set()
        read_a_done.wait(timeout=2.0)
        return sig_b.value + 2

    computed_a = Computed(compute_a)
    computed_b = Computed(compute_b)

    result_a_initial = computed_a()
    assert result_a_initial == 1

    def thread1():
        results["b"] = computed_b()

    def thread2():
        computing_b.wait(timeout=2.0)
        results["a"] = computed_a()
        read_a_done.set()

    t1 = threading.Thread(target=thread1)
    t2 = threading.Thread(target=thread2)

    t1.start()
    t2.start()
    t1.join(timeout=3.0)
    t2.join(timeout=3.0)

    assert results["a"] == 1, f"Expected cached A=1, got {results['a']}"
    assert results["b"] == 3, f"Expected B=3, got {results['b']}"


def test_computed_exception_does_not_deadlock():
    """Exception in computed function should not leave waiters stuck."""
    sig = Signal(0)
    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("First call fails")
        return sig.value

    computed = Computed(flaky)

    with pytest.raises(ValueError, match="First call fails"):
        computed()

    # Second call should work, not deadlock
    assert computed() == 0
    assert call_count == 2  # Both calls attempted


def test_circular_dependency_raises_error():
    """Circular computed dependencies should raise a clear error."""
    import pytest

    computed_a: Computed[int] | None = None
    computed_b: Computed[int] | None = None

    def fn_a():
        return computed_b() + 1 if computed_b else 0

    def fn_b():
        return computed_a() + 1 if computed_a else 0

    computed_a = Computed(fn_a)
    computed_b = Computed(fn_b)

    with pytest.raises(RecursionError, match="Circular dependency detected"):
        computed_a()


def test_computed_track_signal_thread_safe():
    """Computed._track_signal is thread-safe for bidirectional tracking."""
    from wtfui.core.computed import Computed
    from wtfui.core.signal import Signal

    signal = Signal(0)
    computed = Computed(lambda: signal.value * 2)

    errors = []

    def track():
        try:
            for _ in range(100):
                computed._track_signal(signal)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=track) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert signal in computed._tracked_signals
