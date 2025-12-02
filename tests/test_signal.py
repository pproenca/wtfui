# tests/test_signal.py
"""Tests for Signal - a thread-safe reactive value for Python 3.14+ No-GIL builds."""

import threading

from flow.signal import Signal


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
    """Signal handles concurrent updates without tearing (No-GIL safe)."""
    sig = Signal(0)

    def increment():
        for _ in range(100):
            with sig._lock:
                current = sig._value
                sig._value = current + 1
                sig._notify_locked()

    threads = [threading.Thread(target=increment) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Value should be 400 if thread-safe (no lost updates)
    assert sig.value == 400
