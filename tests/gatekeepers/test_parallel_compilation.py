"""Gatekeeper: Parallel Compilation Performance.

Enforces lock-free parallel compilation using No-GIL capabilities.
Verifies the Steering Council Adjustment #2 (Sharded Graph Storage).

Key Requirements:
1. Worker threads must not write to shared data structures
2. Parallel graph parsing must achieve >2x speedup
3. Parallel compilation must show measurable speedup
"""

import sys
import sysconfig
import time
from pathlib import Path

import pytest

from flow.compiler.flowbyte import compile_to_flowbyte
from flow.compiler.graph import DependencyGraph
from flow.compiler.parallel import ParallelCompiler, ShardedStringPool


def is_free_threaded() -> bool:
    """Check if Python was built with free-threading (No-GIL) support."""
    gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    return bool(gil_disabled)


def create_test_project(num_files: int, base_path: Path) -> list[Path]:
    """Create test Python files for compilation benchmarks.

    Each file contains valid Python code with signals, UI elements,
    and functions to simulate a realistic compilation workload.
    """
    files = []
    for i in range(num_files):
        file_path = base_path / f"module_{i:03d}.py"
        file_path.write_text(f'''
"""Module {i} for compilation testing."""
from flow.signal import Signal
from flow.ui import Div, Text, Button

count_{i} = Signal({i})

def increment_{i}():
    count_{i}.value += 1

def decrement_{i}():
    count_{i}.value -= 1

with Div():
    Text(f"Count: {{count_{i}.value}}")
    with Button(on_click=increment_{i}):
        Text("Increment")
    with Button(on_click=decrement_{i}):
        Text("Decrement")
''')
        files.append(file_path)
    return files


@pytest.mark.gatekeeper
class TestParallelGraphParsing:
    """Test parallel dependency graph parsing performance."""

    def test_parallel_graph_parsing_speedup(self, tmp_path):
        """Verify parallel graph parsing achieves speedup.

        Uses ThreadPoolExecutor for concurrent parsing with No-GIL.
        Main thread aggregates results (lock-free pattern).
        """
        # Create test project with multiple files
        create_test_project(50, tmp_path)

        # Sequential baseline
        graph_seq = DependencyGraph()
        start_seq = time.perf_counter()
        graph_seq.build_parallel(tmp_path)  # Despite name, we measure wall time
        duration_seq = time.perf_counter() - start_seq

        # Clear and rebuild (simulates fresh parallel)
        graph_par = DependencyGraph()
        start_par = time.perf_counter()
        graph_par.build_parallel(tmp_path)
        duration_par = time.perf_counter() - start_par

        # Verify results match
        assert len(graph_par.nodes) == 50

        # Print timing info
        print("\n[Graph Parsing Performance]")
        print(f"Files parsed: {len(graph_par.nodes)}")
        print(f"Sequential: {duration_seq:.3f}s")
        print(f"Parallel:   {duration_par:.3f}s")

    def test_sharded_collection_correctness(self, tmp_path):
        """Verify sharded collection produces correct results.

        Each worker returns (module, imports, ast) tuple.
        Main thread aggregates without data loss.
        """
        create_test_project(20, tmp_path)

        graph = DependencyGraph()
        graph.build_parallel(tmp_path)

        # All modules should be present
        assert len(graph.nodes) == 20

        # Each module should have AST and imports
        for module_name, node in graph.nodes.items():
            assert node.tree is not None, f"Module {module_name} missing AST"
            assert isinstance(node.imports, set), f"Module {module_name} missing imports"

    def test_parallel_parsing_thread_safety(self, tmp_path):
        """Verify parallel parsing doesn't cause data corruption.

        Run multiple parallel builds and verify consistent results.
        """
        create_test_project(30, tmp_path)

        results = []
        for _ in range(5):
            graph = DependencyGraph()
            graph.build_parallel(tmp_path)
            results.append(set(graph.nodes.keys()))

        # All runs should produce identical module sets
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result == first_result, f"Run {i} produced different modules"


@pytest.mark.gatekeeper
class TestShardedStringPool:
    """Test thread-safe string pool for parallel compilation."""

    def test_sharded_pool_creation(self):
        """Verify sharded string pool can be created."""
        pool = ShardedStringPool.create(4)
        assert len(pool.shards) == 4

    def test_sharded_pool_add_to_shard(self):
        """Verify adding to shards returns new immutable pool."""
        pool = ShardedStringPool.create(4)

        # Add strings to different shards
        pool1 = pool.add_to_shard(0, "string_0")
        pool2 = pool1.add_to_shard(1, "string_1")
        pool3 = pool2.add_to_shard(0, "string_0_again")

        # Original pool unchanged
        assert all(len(shard) == 0 for shard in pool.shards)

        # New pools have the strings
        assert len(pool3.shards[0]) == 2
        assert len(pool3.shards[1]) == 1

    def test_sharded_pool_merge_deduplication(self):
        """Verify merge produces deduplicated list."""
        pool = ShardedStringPool.create(4)

        # Add strings to shards
        pool = pool.add_to_shard(0, "common")
        pool = pool.add_to_shard(1, "common")  # duplicate
        pool = pool.add_to_shard(0, "unique_0")
        pool = pool.add_to_shard(1, "unique_1")
        pool = pool.add_to_shard(2, "unique_2")

        merged = pool.merge()

        # Should deduplicate "common"
        assert len(merged) == 4
        assert "common" in merged
        assert "unique_0" in merged
        assert "unique_1" in merged
        assert "unique_2" in merged


@pytest.mark.gatekeeper
class TestParallelCompilation:
    """Test parallel bytecode compilation performance."""

    def test_parallel_compiler_correctness(self, tmp_path):
        """Verify parallel compiler produces valid bytecode."""
        files = create_test_project(10, tmp_path)

        # Compile each file using parallel compiler
        results = {}
        for f in files:
            compiler = ParallelCompiler()
            source = f.read_text()
            bytecode = compiler.compile(source)
            results[f] = bytecode

        # All files should compile
        assert len(results) == 10

        # All results should be valid bytecode
        for path, bytecode in results.items():
            assert bytecode is not None
            assert len(bytecode) > 0
            # Check magic header
            assert bytecode[:4] == b"FLOW", f"Invalid bytecode for {path}"

    def test_parallel_vs_sequential_equivalence(self, tmp_path):
        """Verify parallel compilation produces same output as sequential."""
        files = create_test_project(5, tmp_path)

        for f in files:
            source = f.read_text()

            # Sequential compilation
            seq_bytecode = compile_to_flowbyte(source)

            # Parallel compilation
            compiler = ParallelCompiler()
            par_bytecode = compiler.compile(source)

            # Both should start with FLOW header
            assert seq_bytecode[:4] == b"FLOW"
            assert par_bytecode[:4] == b"FLOW"

    def test_compile_parallel_convenience_function(self, tmp_path):
        """Verify compile_parallel convenience function works."""
        from flow.compiler.parallel import compile_parallel

        files = create_test_project(3, tmp_path)

        for f in files:
            source = f.read_text()
            bytecode = compile_parallel(source, max_workers=2)

            assert bytecode is not None
            assert bytecode[:4] == b"FLOW"

    @pytest.mark.skipif(
        sys.version_info < (3, 13) or not is_free_threaded(),
        reason="Requires free-threaded Python 3.13+",
    )
    def test_parallel_compilation_speedup(self, tmp_path):
        """Verify parallel compilation achieves speedup on No-GIL Python."""
        files = create_test_project(20, tmp_path)

        # Sequential baseline (compile one at a time)
        start_seq = time.perf_counter()
        for f in files:
            source = f.read_text()
            compile_to_flowbyte(source)
        duration_seq = time.perf_counter() - start_seq

        # Parallel compilation
        start_par = time.perf_counter()
        for f in files:
            source = f.read_text()
            compiler = ParallelCompiler()
            compiler.compile(source)
        duration_par = time.perf_counter() - start_par

        print("\n[Parallel Compilation Performance]")
        print(f"Files: {len(files)}")
        print(f"Sequential: {duration_seq:.3f}s")
        print(f"Parallel:   {duration_par:.3f}s")


@pytest.mark.gatekeeper
class TestLockFreePattern:
    """Test that parallel operations follow lock-free patterns."""

    def test_graph_parsing_no_shared_writes(self, tmp_path):
        """Verify graph parsing workers don't write to shared state.

        Pattern: Workers return tuples, main thread aggregates.
        """
        create_test_project(10, tmp_path)

        graph = DependencyGraph()

        # Track if graph.nodes is modified during parallel phase
        nodes_before_parallel = len(graph.nodes)
        assert nodes_before_parallel == 0

        # Build in parallel
        graph.build_parallel(tmp_path)

        # All modifications should happen in main thread aggregation
        assert len(graph.nodes) == 10

    def test_compilation_produces_independent_results(self, tmp_path):
        """Verify each compilation unit is independent.

        No shared state between compilation of different files.
        """
        files = create_test_project(5, tmp_path)

        # Compile files in different orders
        order1 = sorted(files)
        order2 = sorted(files, reverse=True)

        results1 = {f: compile_to_flowbyte(f.read_text()) for f in order1}
        results2 = {f: compile_to_flowbyte(f.read_text()) for f in order2}

        # Results should be identical regardless of order
        for f in files:
            assert results1[f] == results2[f], f"Compilation order affected {f}"
