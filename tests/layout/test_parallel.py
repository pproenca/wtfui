# tests/test_layout_parallel.py
"""Tests for parallel layout computation using No-GIL Python 3.14+."""

import time
from concurrent.futures import ThreadPoolExecutor

from wtfui.tui.layout.compute import compute_layout
from wtfui.tui.layout.node import LayoutNode
from wtfui.tui.layout.parallel import compute_layout_parallel, find_layout_boundaries
from wtfui.tui.layout.style import FlexDirection, FlexStyle
from wtfui.tui.layout.types import Dimension, Size


class TestParallelLayout:
    def test_parallel_layout_same_result(self):
        """Parallel layout produces same result as sequential."""

        def create_tree() -> LayoutNode:
            parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))
            for _ in range(5):
                child = LayoutNode(
                    style=FlexStyle(
                        width=Dimension.points(50),
                        height=Dimension.points(30),
                    )
                )
                parent.add_child(child)
            return parent

        available = Size(width=300, height=100)

        # Compute sequential
        seq_tree = create_tree()
        compute_layout(seq_tree, available)
        sequential_results = [
            (c.layout.x, c.layout.y, c.layout.width, c.layout.height) for c in seq_tree.children
        ]

        # Compute parallel on fresh tree
        par_tree = create_tree()
        compute_layout_parallel(par_tree, available)
        parallel_results = [
            (c.layout.x, c.layout.y, c.layout.width, c.layout.height) for c in par_tree.children
        ]

        assert sequential_results == parallel_results

    def test_parallel_layout_nested(self):
        """Parallel layout works with nested structures."""
        root = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        # Create 3 branches that can be computed in parallel
        for _ in range(3):
            branch = LayoutNode(
                style=FlexStyle(
                    flex_direction=FlexDirection.COLUMN,
                    width=Dimension.points(100),
                )
            )
            root.add_child(branch)

            for _ in range(4):
                leaf = LayoutNode(
                    style=FlexStyle(
                        height=Dimension.points(25),
                    )
                )
                branch.add_child(leaf)

        available = Size(width=400, height=200)
        compute_layout_parallel(root, available)

        # Verify all nodes have layouts
        assert root.layout is not None
        for branch in root.children:
            assert branch.layout is not None
            for leaf in branch.children:
                assert leaf.layout is not None

    def test_parallel_layout_many_siblings(self):
        """Parallel layout handles many siblings efficiently."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        # Many children that could be parallelized
        for _ in range(100):
            child = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(10),
                    height=Dimension.points(20),
                )
            )
            parent.add_child(child)

        available = Size(width=1000, height=100)
        compute_layout_parallel(parent, available)

        assert parent.layout is not None
        assert all(c.layout is not None for c in parent.children)

    def test_parallel_layout_empty(self):
        """Parallel layout handles empty trees."""
        root = LayoutNode(style=FlexStyle())
        compute_layout_parallel(root, Size(width=100, height=100))
        assert root.layout is not None

    def test_parallel_layout_single_child(self):
        """Parallel layout handles single child (no parallelism needed)."""
        parent = LayoutNode(style=FlexStyle())
        child = LayoutNode(style=FlexStyle(width=Dimension.points(50), height=Dimension.points(30)))
        parent.add_child(child)

        compute_layout_parallel(parent, Size(width=100, height=100))

        assert parent.layout is not None
        assert child.layout is not None

    def test_parallel_with_custom_executor(self):
        """Parallel layout accepts custom ThreadPoolExecutor."""
        parent = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        for _ in range(5):
            child = LayoutNode(
                style=FlexStyle(
                    width=Dimension.points(20),
                    height=Dimension.points(20),
                )
            )
            parent.add_child(child)

        with ThreadPoolExecutor(max_workers=2) as executor:
            compute_layout_parallel(
                parent,
                Size(width=200, height=100),
                executor=executor,
            )

        assert parent.layout is not None


class TestParallelPerformance:
    """Performance tests for parallel layout (optional, may be slow)."""

    def test_large_tree_completes(self):
        """Large tree layout completes within reasonable time."""
        # Build a tree with 1000 nodes
        root = LayoutNode(style=FlexStyle(flex_direction=FlexDirection.ROW))

        for _ in range(10):
            branch = LayoutNode(
                style=FlexStyle(
                    flex_direction=FlexDirection.COLUMN,
                    width=Dimension.points(100),
                )
            )
            root.add_child(branch)

            for _ in range(10):
                sub_branch = LayoutNode(
                    style=FlexStyle(
                        flex_direction=FlexDirection.ROW,
                        height=Dimension.points(20),
                    )
                )
                branch.add_child(sub_branch)

                for _ in range(10):
                    leaf = LayoutNode(
                        style=FlexStyle(
                            width=Dimension.points(10),
                            height=Dimension.points(10),
                        )
                    )
                    sub_branch.add_child(leaf)

        available = Size(width=1000, height=500)

        start = time.perf_counter()
        compute_layout_parallel(root, available)
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms per success criteria
        assert elapsed < 0.1, f"Layout took {elapsed * 1000:.1f}ms, expected < 100ms"

        # Verify all nodes computed
        def count_nodes(node: LayoutNode) -> int:
            return 1 + sum(count_nodes(c) for c in node.children)

        total = count_nodes(root)
        assert total == 1111  # 1 + 10 + 100 + 1000


class TestLayoutBoundaries:
    """Tests for Layout Boundary detection (Amendment Gamma)."""

    def test_find_boundaries_in_tree(self):
        """Finds all Layout Boundary nodes in tree."""
        root = LayoutNode(style=FlexStyle())

        # Non-boundary children
        child1 = LayoutNode(style=FlexStyle(flex_grow=1.0))

        # Layout Boundary child (has explicit w & h)
        child2 = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )

        # Grandchildren under boundary
        grandchild = LayoutNode(style=FlexStyle(flex_grow=1.0))

        root.add_child(child1)
        root.add_child(child2)
        child2.add_child(grandchild)

        boundaries = find_layout_boundaries(root)

        assert child2 in boundaries
        assert root not in boundaries  # Root is not a boundary
        assert child1 not in boundaries  # No fixed dimensions
        assert grandchild not in boundaries  # No fixed dimensions

    def test_node_is_layout_boundary(self):
        """LayoutNode.is_layout_boundary() works correctly."""
        # With explicit width and height
        boundary = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(50),
            )
        )
        assert boundary.is_layout_boundary()

        # Without explicit dimensions
        non_boundary = LayoutNode(style=FlexStyle(flex_grow=1.0))
        assert not non_boundary.is_layout_boundary()

        # With only width
        width_only = LayoutNode(style=FlexStyle(width=Dimension.points(100)))
        assert not width_only.is_layout_boundary()

        # With only height
        height_only = LayoutNode(style=FlexStyle(height=Dimension.points(50)))
        assert not height_only.is_layout_boundary()

    def test_find_multiple_boundaries(self):
        """Finds multiple boundaries at different depths."""
        root = LayoutNode(style=FlexStyle())

        b1 = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(100),
                height=Dimension.points(100),
            )
        )
        b2 = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(200),
                height=Dimension.points(200),
            )
        )

        root.add_child(b1)
        root.add_child(b2)

        # Nested boundary under b1
        b3 = LayoutNode(
            style=FlexStyle(
                width=Dimension.points(50),
                height=Dimension.points(50),
            )
        )
        b1.add_child(b3)

        boundaries = find_layout_boundaries(root)

        assert len(boundaries) == 3
        assert b1 in boundaries
        assert b2 in boundaries
        assert b3 in boundaries
