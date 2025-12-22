# tests/test_signal.py
"""Tests for Signal - a thread-safe reactive value for Python 3.14+ No-GIL builds."""

import threading

from wtfui.core.signal import Signal


def test_signal_stores_initial_value():
    """Signal stores and returns its initial value."""
    sig = Signal(42)
    assert sig.value == 42


def test_signal_updates_value():
    """Signal value can be updated."""
    sig = Signal(0)
    sig.value = 100
    assert sig.value == 100


def test_signal_no_notify_on_same_value():
    """Signal does not notify when value unchanged."""
    notifications: list[str] = []

    sig = Signal(5)
    sig.subscribe(lambda: notifications.append("called"))

    sig.value = 5  # Same value
    assert notifications == []


def test_signal_notifies_on_change():
    """Signal notifies subscribers when value changes."""
    notifications: list[str] = []

    sig = Signal(0)
    sig.subscribe(lambda: notifications.append("called"))

    sig.value = 1
    assert notifications == ["called"]


def test_signal_multiple_subscribers():
    """Signal notifies all subscribers."""
    calls: list[str] = []

    sig = Signal("a")
    sig.subscribe(lambda: calls.append("sub1"))
    sig.subscribe(lambda: calls.append("sub2"))

    sig.value = "b"
    # Order is not guaranteed (set-based), but both should be called
    assert sorted(calls) == ["sub1", "sub2"]


def test_signal_generic_typing():
    """Signal supports generic types."""
    sig_int: Signal[int] = Signal(0)
    sig_str: Signal[str] = Signal("")

    sig_int.value = 42
    sig_str.value = "hello"

    assert sig_int.value == 42
    assert sig_str.value == "hello"


def test_signal_thread_safety():
    """Signal handles concurrent reads without crashing (No-GIL safe)."""
    sig = Signal(0)
    read_values: list[int] = []
    lock = threading.Lock()

    def reader():
        for _ in range(100):
            val = sig.value
            with lock:
                read_values.append(val)

    def writer():
        for i in range(100):
            sig.value = i

    # Run readers and writers concurrently
    threads = [
        threading.Thread(target=reader),
        threading.Thread(target=reader),
        threading.Thread(target=writer),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All reads should have completed (200 reads from 2 readers)
    assert len(read_values) == 200
    # All values should be valid integers (no corruption)
    assert all(isinstance(v, int) for v in read_values)


def test_effect_garbage_collected_when_disposed():
    """Effects should be garbage collected after dispose() is called."""
    import gc
    import weakref

    from wtfui.core.effect import Effect

    sig = Signal(0)

    def effect_fn() -> None:
        _ = sig.value

    effect = Effect(effect_fn)
    effect_ref = weakref.ref(effect)

    # Effect should be tracked
    assert len(sig._effects) == 1

    # Dispose and delete
    effect.dispose()
    del effect
    gc.collect()

    # Effect should be garbage collected
    assert effect_ref() is None
    assert len(sig._effects) == 0


def test_computed_garbage_collected_when_disposed():
    """Computeds should be garbage collected after dispose() is called."""
    import gc
    import weakref

    from wtfui.core.computed import Computed

    sig = Signal(0)
    computed = Computed(lambda: sig.value * 2)
    _ = computed()  # Trigger dependency tracking
    computed_ref = weakref.ref(computed)

    # Computed should be tracked
    assert len(sig._computeds) == 1

    # Dispose and delete
    computed.dispose()
    del computed
    gc.collect()

    # Computed should be garbage collected
    assert computed_ref() is None
    assert len(sig._computeds) == 0


def test_signal_no_nested_lock_deadlock():
    """Signal.value access should not cause deadlock from nested locking."""
    import time

    from wtfui.core.effect import Effect

    signal = Signal(0)
    results = []
    deadlock_detected = threading.Event()

    def reader():
        for _ in range(100):
            _ = signal.value
            results.append(1)

    def effect_fn():
        _ = signal.value

    _ = Effect(effect_fn)  # Create effect to track signal

    threads = [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()

    timeout = 2.0
    start = time.perf_counter()
    for t in threads:
        remaining = timeout - (time.perf_counter() - start)
        if remaining <= 0:
            deadlock_detected.set()
            break
        t.join(timeout=remaining)
        if t.is_alive():
            deadlock_detected.set()
            break

    assert not deadlock_detected.is_set(), "Potential deadlock from nested locking"
    assert len(results) == 400
