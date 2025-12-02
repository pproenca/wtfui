# tests/test_effect.py
"""Tests for Effect - thread-safe dependency tracking for Python 3.14+ No-GIL builds."""

import threading

from flow.effect import Effect, get_running_effect
from flow.signal import Signal


def test_effect_runs_function_immediately():
    """Effect executes its function on creation."""
    calls: list[str] = []
    Effect(lambda: calls.append("ran"))
    assert calls == ["ran"]


def test_effect_tracks_signal_access():
    """Effect automatically tracks signals read during execution."""
    count = Signal(0)
    computed_values: list[int] = []

    def compute():
        computed_values.append(count.value * 2)

    Effect(compute)
    assert computed_values == [0]  # Initial run

    count.value = 5
    assert computed_values == [0, 10]  # Re-ran after signal change


def test_effect_tracks_multiple_signals():
    """Effect tracks multiple signal dependencies."""
    a = Signal(1)
    b = Signal(2)
    results: list[int] = []

    def compute():
        results.append(a.value + b.value)

    Effect(compute)
    assert results == [3]

    a.value = 10
    assert results == [3, 12]

    b.value = 20
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
    results: dict[str, list[int]] = {"thread1": [], "thread2": []}
    sig1 = Signal(0)
    sig2 = Signal(0)

    def thread1_work():
        def track():
            results["thread1"].append(sig1.value)

        Effect(track)
        sig1.value = 10

    def thread2_work():
        def track():
            results["thread2"].append(sig2.value)

        Effect(track)
        sig2.value = 20

    t1 = threading.Thread(target=thread1_work)
    t2 = threading.Thread(target=thread2_work)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert 0 in results["thread1"] and 10 in results["thread1"]
    assert 0 in results["thread2"] and 20 in results["thread2"]
