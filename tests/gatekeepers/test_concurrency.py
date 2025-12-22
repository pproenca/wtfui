"""Gatekeeper: Parallel Scaling.

Enforces Tenet IV (Native Leverage) by proving that Python 3.14
threads are actually parallel (No-GIL free-threading).

Threshold: 4 threads must be > 1.3x faster than sequential (best of 3 trials).

Note: The speedup threshold is conservative (1.3x vs theoretical 4x) because:
1. Memory allocator contention exists even without GIL
2. CPU cache effects reduce parallelism benefits
3. Thread scheduling overhead
4. System load variance during test execution

The key insight is that with GIL, speedup would be ~1.0x (no benefit),
so any speedup > 1.2x proves No-GIL is working. The test uses multiple
trials and takes the best result to handle transient system load.
"""

import sys
import sysconfig
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.types import Size

from .conftest import generate_deep_layout_tree

if TYPE_CHECKING:
    from wtfui.tui.layout.node import LayoutNode

# Test configuration constants
ITERATIONS = 20  # Number of layout computations per test
WORKERS = 4  # Number of parallel workers
MIN_SPEEDUP = 1.3  # Minimum required parallel speedup (with GIL would be ~1.0x)
WARMUP_ITERATIONS = 5  # Warmup runs to stabilize CPU frequency and caches
TRIALS = 3  # Number of trials to run (takes best result to handle system load variance)


def is_free_threaded() -> bool:
    """Check if Python was built with free-threading (No-GIL) support."""
    # Check Py_GIL_DISABLED config var (1 = free-threaded build)
    gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    return bool(gil_disabled)


def has_gil_incompatible_deps() -> bool:
    """Check if any dependencies would re-enable the GIL.

    Some packages like greenlet (used by asyncio/anyio) don't support
    free-threading and will force the GIL back on when imported.
    """
    try:
        import greenlet  # type: ignore  # noqa: F401

        return True  # greenlet re-enables GIL
    except ImportError:
        return False


@pytest.mark.gatekeeper
def test_no_greenlet_dependency() -> None:
    """Gatekeeper: Reject greenlet dependency.

    ADR-0001 mandates: Flow uses asyncio + ThreadPoolExecutor, not greenlet.

    Greenlet would:
    1. Re-enable the GIL in free-threaded Python builds
    2. Add binary dependency (violates Tenet III: Zero-Friction)
    3. Provide only cooperative multitasking (no true parallelism)

    This test fails if greenlet is importable, preventing accidental
    introduction via transitive dependencies.
    """
    greenlet_available = False
    try:
        import greenlet  # noqa: F401

        greenlet_available = True
    except ImportError:
        pass

    assert not greenlet_available, (
        "ARCHITECTURAL VIOLATION: greenlet detected!\n"
        "Flow requires native Python concurrency (asyncio + threading).\n"
        "greenlet re-enables the GIL and violates ADR-0001.\n"
        "Remove the dependency that pulls in greenlet."
    )


@pytest.mark.gatekeeper
@pytest.mark.skipif(
    sys.version_info < (3, 13) or not is_free_threaded(),
    reason="Requires free-threaded Python 3.13+ (install with: uv python install 3.13t)",
)
@pytest.mark.xfail(
    condition=has_gil_incompatible_deps(),
    reason="greenlet dependency re-enables GIL (awaiting ecosystem support)",
    strict=False,
)
def test_no_gil_throughput() -> None:
    """
    Gatekeeper: Parallel Scaling.

    Threshold: 4 threads must be > 1.3x faster than sequential.

    If GIL is active, speedup is usually < 1.1x due to overhead.
    If No-GIL is active, speedup should be significantly higher.

    The test runs multiple trials and takes the best result to handle
    system load variance. This prevents flaky failures when the system
    is temporarily under load while still catching real GIL issues.

    The test pre-allocates trees to minimize memory allocator contention,
    which exists regardless of GIL status and would mask the parallelism benefits.
    """

    def run_heavy_layout(tree: LayoutNode) -> bool:
        """Compute layout on a pre-allocated tree."""
        compute_layout(tree, Size(1000, 1000))
        return True

    def run_single_trial() -> tuple[float, float, float]:
        """Run one trial of sequential vs parallel comparison.

        Returns (sequential_time, parallel_time, speedup).
        """
        # Pre-allocate trees for sequential test
        # Using depth=8, width=3 gives ~9841 nodes per tree (enough work to show parallelism)
        seq_trees = [generate_deep_layout_tree(depth=8, width=3) for _ in range(ITERATIONS)]

        # Sequential Baseline
        start_seq = time.perf_counter()
        for tree in seq_trees:
            run_heavy_layout(tree)
        duration_seq = time.perf_counter() - start_seq

        # Pre-allocate fresh trees for parallel test (layout modifies node state)
        par_trees = [generate_deep_layout_tree(depth=8, width=3) for _ in range(ITERATIONS)]

        # Parallel Execution (The No-GIL Test)
        start_par = time.perf_counter()
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            results = list(executor.map(run_heavy_layout, par_trees))
        duration_par = time.perf_counter() - start_par

        assert all(results), "Some parallel tasks failed"

        speedup = duration_seq / duration_par
        return duration_seq, duration_par, speedup

    # Warmup: Stabilize CPU frequency scaling and warm caches
    # This prevents cold-start effects from skewing the benchmark
    warmup_trees = [generate_deep_layout_tree(depth=8, width=3) for _ in range(WARMUP_ITERATIONS)]
    for tree in warmup_trees:
        run_heavy_layout(tree)

    # Run multiple trials and collect results
    # This handles system load variance - if one trial is affected by
    # a background process, others may not be
    trial_results: list[tuple[float, float, float]] = []
    for _trial in range(TRIALS):
        seq_time, par_time, speedup = run_single_trial()
        trial_results.append((seq_time, par_time, speedup))

    # Use the best speedup from all trials
    # This is fair because we're testing for capability, not average performance
    best_trial = max(trial_results, key=lambda x: x[2])
    best_seq, best_par, best_speedup = best_trial
    all_speedups = [r[2] for r in trial_results]

    print("\n[No-GIL Gatekeeper]")
    print(f"Trials: {TRIALS} (best-of-N to handle system load variance)")
    print(f"Speedups: {', '.join(f'{s:.2f}x' for s in all_speedups)}")
    print("Best trial:")
    print(f"  Sequential: {best_seq:.3f}s ({ITERATIONS} iterations)")
    print(f"  Parallel:   {best_par:.3f}s ({WORKERS} workers)")
    print(f"  Speedup:    {best_speedup:.2f}x")

    assert best_speedup > MIN_SPEEDUP, (
        f"GIL Detected! Best speedup {best_speedup:.2f}x is insufficient for {WORKERS} cores. "
        f"Expected > {MIN_SPEEDUP}x. All trials: {all_speedups}"
    )


@pytest.mark.gatekeeper
def test_layout_thread_safety() -> None:
    """Verify layout computation is thread-safe.

    Multiple threads computing independent trees should not
    interfere with each other's results.
    """
    from wtfui.tui.layout.node import LayoutNode
    from wtfui.tui.layout.style import FlexStyle
    from wtfui.tui.layout.types import Dimension

    def compute_and_verify(expected_width: float) -> tuple[bool, float]:
        """Compute layout and verify result matches expected."""
        style = FlexStyle(
            width=Dimension.points(expected_width),
            height=Dimension.points(100),
        )
        node = LayoutNode(style=style)
        compute_layout(node, Size(1000, 1000))
        return node.layout.width == expected_width, node.layout.width

    # Run many parallel computations with different expected values
    widths = list(range(10, 110, 10))  # 10, 20, 30, ... 100

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(compute_and_verify, widths))

    for i, (success, actual) in enumerate(results):
        expected = widths[i]
        assert success, f"Thread safety violation: expected {expected}, got {actual}"

    print(f"\n[Thread Safety] {len(widths)} parallel computations verified")
