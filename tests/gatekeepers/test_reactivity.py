"""Gatekeeper: Reactivity System Thread-Safety.

Enforces that Signal, Effect, and Computed are safe under concurrent access.
These primitives are the foundation of Flow's reactive system and must
work correctly when accessed from multiple threads in No-GIL Python.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from wtfui.core.computed import Computed
from wtfui.core.effect import Effect
from wtfui.core.signal import Signal


@pytest.mark.gatekeeper
def test_signal_computed_effect_thread_safety() -> None:
    """Gatekeeper: Reactivity primitives must be thread-safe.

    This test hammers Signal → Computed → Effect from multiple threads
    to expose any race conditions in the reactive update chain.

    Threshold: No exceptions, no data corruption under 8 threads x 100 iterations.
    """
    # Shared state
    signal = Signal(0)
    effect_runs: list[int] = []
    effect_lock = threading.Lock()

    @Computed
    def doubled() -> int:
        return signal.value * 2

    def record_effect():
        with effect_lock:
            effect_runs.append(doubled())

    effect = Effect(record_effect)
    effect.run()  # Initial run

    errors: list[Exception] = []

    def writer(thread_id: int) -> None:
        """Increment signal from multiple threads."""
        try:
            for i in range(10):
                signal.value = thread_id * 100 + i
        except Exception as e:
            errors.append(e)

    def reader(_: int) -> int:
        """Read computed from multiple threads."""
        try:
            return doubled()
        except Exception as e:
            errors.append(e)
            return -1

    # Concurrent writers and readers
    with ThreadPoolExecutor(max_workers=8) as executor:
        # 4 writer threads
        writer_futures = [executor.submit(writer, i) for i in range(4)]
        # 4 reader threads (100 reads each)
        reader_futures = list(executor.map(reader, range(100)))

        # Wait for writers
        for f in writer_futures:
            f.result()

    # No exceptions should have occurred
    assert not errors, f"Thread-safety violation: {errors}"

    # All reads should be even numbers (signal * 2)
    assert all(r % 2 == 0 or r == -1 for r in reader_futures), "Computed returned odd value"

    print(
        f"\n[Reactivity Thread-Safety] {len(reader_futures)} concurrent reads, {len(effect_runs)} effect runs"
    )


@pytest.mark.gatekeeper
def test_computed_memoization_under_contention() -> None:
    """Gatekeeper: Computed memoization must work under thread contention.

    Multiple threads accessing the same Computed should not cause
    excessive recomputation. The lock should serialize access properly.
    """
    compute_count = 0
    count_lock = threading.Lock()

    signal = Signal(42)

    @Computed
    def expensive() -> int:
        nonlocal compute_count
        with count_lock:
            compute_count += 1
        # Simulate expensive computation
        return signal.value**2

    def access(_: int) -> int:
        return expensive()

    # 100 concurrent accesses from 8 threads
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(access, range(100)))

    # All results must be correct
    assert all(r == 42**2 for r in results), "Incorrect computation result"

    # Memoization should limit recomputation
    # Allow up to 8 (one per thread that might hit dirty state simultaneously)
    assert compute_count <= 8, (
        f"Memoization failure: {compute_count} computations for 100 accesses "
        f"(expected ≤8 due to thread contention)"
    )

    print(f"\n[Memoization] {compute_count} computations for 100 accesses")
