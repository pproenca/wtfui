"""Layout algorithm performance gatekeepers.

These tests establish baseline performance metrics for the layout engine.
Run with: ./dev test:gate -k "layout_perf"
"""

import time

import pytest

from tests.gatekeepers.utils import generate_deep_layout_tree, generate_wide_layout_tree
from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.types import Size


def test_generate_wide_layout_tree():
    """Wide tree generator creates correct structure."""
    tree = generate_wide_layout_tree(width=100)
    assert len(tree.children) == 100


def test_generate_deep_layout_tree():
    """Deep tree generator creates correct structure."""
    tree = generate_deep_layout_tree(depth=5, width=1)
    # Count depth
    depth = 0
    node = tree
    while node.children:
        depth += 1
        node = node.children[0]
    assert depth == 5


@pytest.mark.gatekeeper
def test_layout_wide_tree_latency():
    """Gatekeeper: Wide layout tree (1000 siblings) computes in <50ms."""
    root = generate_wide_layout_tree(width=1000)

    # Warm-up
    compute_layout(root, Size(1920, 1080))

    # Reset and measure
    root = generate_wide_layout_tree(width=1000)
    start = time.perf_counter()
    compute_layout(root, Size(1920, 1080))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.050, f"Wide tree layout took {elapsed * 1000:.1f}ms, expected <50ms"


@pytest.mark.gatekeeper
def test_layout_deep_tree_latency():
    """Gatekeeper: Deep layout tree (50 levels) computes in <50ms."""
    root = generate_deep_layout_tree(depth=50, width=1)

    # Warm-up
    compute_layout(root, Size(1920, 1080))

    # Reset and measure
    root = generate_deep_layout_tree(depth=50, width=1)
    start = time.perf_counter()
    compute_layout(root, Size(1920, 1080))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.050, f"Deep tree layout took {elapsed * 1000:.1f}ms, expected <50ms"


@pytest.mark.gatekeeper
def test_layout_complex_tree_latency():
    """Gatekeeper: Complex tree (6 depth x 4 width) computes in <200ms."""
    root = generate_deep_layout_tree(depth=6, width=4)

    def count_nodes(node) -> int:
        return 1 + sum(count_nodes(c) for c in node.children)

    node_count = count_nodes(root)

    start = time.perf_counter()
    compute_layout(root, Size(1920, 1080))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.200, (
        f"Complex tree ({node_count} nodes) took {elapsed * 1000:.1f}ms, expected <200ms"
    )


@pytest.mark.gatekeeper
def test_layout_incremental_baseline():
    """Gatekeeper: Establish baseline for future incremental layout optimization."""
    root = generate_deep_layout_tree(depth=5, width=5)

    times = []
    for _ in range(5):
        root = generate_deep_layout_tree(depth=5, width=5)
        start = time.perf_counter()
        compute_layout(root, Size(1920, 1080))
        times.append(time.perf_counter() - start)

    median = sorted(times)[len(times) // 2]
    print(f"\nLayout baseline: {median * 1000:.2f}ms median for 5x5 tree")

    assert median < 1.0, "Sanity check: layout should complete in <1s"
