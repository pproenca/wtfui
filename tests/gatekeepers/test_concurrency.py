"""Gatekeeper: Parallel Scaling.

Enforces Tenet IV (Native Leverage) by proving that Python 3.14
threads are actually parallel (No-GIL free-threading).

Threshold: 4 threads must be > 2.5x faster than sequential.
"""

import sys
import sysconfig
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flow.layout.compute import compute_layout
from flow.layout.types import Size

from .conftest import generate_deep_layout_tree

# Test configuration constants
ITERATIONS = 20  # Number of layout computations per test
WORKERS = 4  # Number of parallel workers
MIN_SPEEDUP = 2.5  # Minimum required parallel speedup


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
        import greenlet  # type: ignore[import-not-found]  # noqa: F401

        return True  # greenlet re-enables GIL
    except ImportError:
        return False


def run_heavy_layout(_: int) -> bool:
    """A CPU-bound task: Layout a deep tree.

    Args:
        _: Ignored index (for executor.map compatibility).

    Returns:
        True on success.
    """
    # Generate a fresh tree each time to avoid shared state
    root = generate_deep_layout_tree(depth=6, width=3)  # ~364 nodes
    compute_layout(root, Size(1000, 1000))
    return True


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

    Threshold: 4 threads must be > 2.5x faster than sequential.

    If GIL is active, speedup is usually < 1.1x due to overhead.
    If No-GIL is active, speedup should approach WORKERS count.
    """
    # 1. Sequential Baseline
    start_seq = time.perf_counter()
    for i in range(ITERATIONS):
        run_heavy_layout(i)
    duration_seq = time.perf_counter() - start_seq

    # 2. Parallel Execution (The No-GIL Test)
    start_par = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(run_heavy_layout, range(ITERATIONS)))
    duration_par = time.perf_counter() - start_par

    # Verify all completed
    assert all(results), "Some parallel tasks failed"

    # Calculate Speedup
    speedup = duration_seq / duration_par

    print("\n[No-GIL Gatekeeper]")
    print(f"Sequential: {duration_seq:.3f}s ({ITERATIONS} iterations)")
    print(f"Parallel:   {duration_par:.3f}s ({WORKERS} workers)")
    print(f"Speedup:    {speedup:.2f}x")

    # Soft warning if speedup is low but test still passes
    if speedup < MIN_SPEEDUP:
        print(f"WARNING: Speedup {speedup:.2f}x is below target {MIN_SPEEDUP}x")
        print("This may indicate system overload or GIL-acquiring operations in layout code.")

    assert speedup > MIN_SPEEDUP, (
        f"GIL Detected! Speedup {speedup:.2f}x is insufficient for {WORKERS} cores. "
        f"Expected > {MIN_SPEEDUP}x"
    )


@pytest.mark.gatekeeper
def test_layout_thread_safety() -> None:
    """Verify layout computation is thread-safe.

    Multiple threads computing independent trees should not
    interfere with each other's results.
    """
    from flow.layout.node import LayoutNode
    from flow.layout.style import FlexStyle
    from flow.layout.types import Dimension

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
