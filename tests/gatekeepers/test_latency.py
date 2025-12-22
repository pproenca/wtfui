"""Gatekeeper: Reactivity Propagation Speed.

Enforces Tenet V (Atomic Reactivity) by validating that the
invalidation and recomputation algorithms are O(N).

Threshold: < 5ms for invalidating and recomputing 1,000 subscribers.
"""

from typing import Any

import pytest

from wtfui import Computed, Signal

# Test configuration constants
FAN_WIDTH = 1_000  # Number of computed dependents for fan-out test
MAX_TIME_MS = 5.0  # Maximum allowed propagation time in milliseconds
UPDATE_ITERATIONS = 10_000  # Number of updates for no-subscriber test


def create_fan_out(width: int) -> tuple[Signal[int], list[Computed[int]]]:
    """Create a Signal with many Computed dependents (fan-out pattern).

    This tests the real-world scenario of one signal updating many computeds.

    Args:
        width: Number of Computed nodes depending on the signal.

    Returns:
        Tuple of (root Signal, list of Computed values).
    """
    root: Signal[int] = Signal(0)

    # All computeds depend on the root signal
    # Use explicit default args to capture values at definition time
    def make_computed(signal: Signal[int] = root, offset: int = 0) -> Computed[int]:
        def compute(s: Signal[int] = signal, o: int = offset) -> int:
            return s.value + o

        return Computed(compute)

    computeds = [make_computed(root, i) for i in range(width)]

    return root, computeds


@pytest.mark.gatekeeper
@pytest.mark.benchmark(group="reactivity")
def test_pulse_latency(benchmark: Any) -> None:
    """
    Gatekeeper: Reactivity Propagation Speed.

    Threshold: < 5ms for invalidating and recomputing 1,000 dependents.

    Measures how fast signal changes propagate to dependent Computed values.
    The fan-out pattern is more representative of real UI scenarios where
    one state update affects many components.
    """
    root, computeds = create_fan_out(FAN_WIDTH)

    def run_propagation() -> int:
        # Trigger update at root
        root.value += 1
        # Access all computeds to force re-computation
        return sum(c() for c in computeds)

    # Warmup - ensure first run registers dependencies
    _ = run_propagation()

    # Benchmark the operation
    result = benchmark(run_propagation)

    # Verify computation works (sum of 0..999 + root.value*1000)
    expected = sum(range(FAN_WIDTH)) + root.value * FAN_WIDTH
    assert result == expected

    # Get timing (benchmark.stats.stats.mean is in seconds)
    avg_time_ms = benchmark.stats.stats.mean * 1000

    print(f"\n[Pulse Gatekeeper] 1k Fan-out: {avg_time_ms:.4f} ms")
    print(f"[Pulse Gatekeeper] Iterations: {benchmark.stats.stats.rounds}")

    assert avg_time_ms < MAX_TIME_MS, (
        f"System Pulse too slow! {avg_time_ms:.4f}ms > {MAX_TIME_MS}ms"
    )


@pytest.mark.gatekeeper
def test_signal_update_no_subscribers() -> None:
    """Fast path: Signal updates with no subscribers should be O(1)."""
    signal: Signal[int] = Signal(0)

    # Update many times - should not accumulate cost
    for i in range(UPDATE_ITERATIONS):
        signal.value = i

    assert signal.value == UPDATE_ITERATIONS - 1
