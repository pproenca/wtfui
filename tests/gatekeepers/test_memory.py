"""Gatekeeper: Memory Usage per Node.

Enforces Tenet III (Zero-Friction) by ensuring Python objects
are lightweight enough for massive UI trees.

Threshold: < 2KB per fully hydrated node.
"""

import gc
import tracemalloc

import pytest

from wtfui import Signal
from wtfui.ui.elements import Div


class ComplexItem(Div):
    """A representative 'real world' component with props, children, and signals."""

    def __init__(self, idx: int) -> None:
        self.active = Signal(False)
        super().__init__(
            cls=f"item-{idx} p-4 flex",
            id=f"node-{idx}",
        )
        # Store index for potential child element creation
        self._idx = idx


@pytest.mark.gatekeeper
def test_molecular_weight(clean_gc: None) -> None:
    """
    Gatekeeper: Memory Usage per Node.

    Threshold: < 2KB per fully hydrated node.

    Measures the average memory footprint of Flow elements including:
    - Element instance with props
    - Signal for reactive state
    - Child relationships
    """
    NODE_COUNT = 10_000
    MAX_BYTES_PER_NODE = 2048  # 2KB threshold

    # 1. Warmup and cleanup to stabilize baseline
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # 2. Bulk Instantiation
    # Store in list to prevent GC during measurement
    nodes = [ComplexItem(i) for i in range(NODE_COUNT)]

    # 3. Measurement
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Calculate delta
    stats = snapshot2.compare_to(snapshot1, "lineno")
    total_diff = sum(stat.size_diff for stat in stats)

    avg_per_node = total_diff / NODE_COUNT

    # Keep nodes alive until after measurement
    assert len(nodes) == NODE_COUNT

    print(f"\n[Memory Gatekeeper] Average Size: {avg_per_node:.2f} bytes/node")
    print(f"[Memory Gatekeeper] Total for {NODE_COUNT:,} nodes: {total_diff / 1024:.2f} KB")

    # STERN ASSERTION
    assert avg_per_node < MAX_BYTES_PER_NODE, (
        f"Molecular Weight Exceeded! {avg_per_node:.2f} bytes > {MAX_BYTES_PER_NODE} bytes"
    )
