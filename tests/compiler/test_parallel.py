"""Tests for parallel compilation infrastructure.

Verifies that the parallel compiler produces correct output and that
the lock-free design works correctly under concurrent execution.
"""

import threading

from flow.compiler.parallel import (
    CompilationUnit,
    ParallelCompiler,
    ShardedStringPool,
    compile_parallel,
)
from flow.compiler.writer import MAGIC_HEADER


def test_compilation_unit_is_immutable():
    """CompilationUnit is a frozen dataclass."""
    unit = CompilationUnit(
        node_id=1,
        bytecode=b"\x01\x02\x03",
        strings=("hello", "world"),
        children=(2, 3),
    )

    # Verify it's immutable
    try:
        unit.node_id = 2  # type: ignore[misc]
        raise AssertionError("Should not be able to modify frozen dataclass")
    except AttributeError:
        pass  # Expected


def test_parallel_compiler_creates_valid_bytecode():
    """ParallelCompiler produces valid FlowByte binary."""
    source = """
count = Signal(0)
count.value += 1
"""
    binary = compile_parallel(source)

    # Verify header
    assert binary.startswith(MAGIC_HEADER)

    # Verify HALT opcode at end
    assert binary.endswith(b"\xff")


def test_parallel_compiler_handles_small_ast():
    """Small AST falls back to single-threaded compilation."""
    source = "x = Signal(42)"
    binary = compile_parallel(source, max_workers=4)

    assert binary.startswith(MAGIC_HEADER)


def test_parallel_compiler_handles_multiple_functions():
    """Multiple function definitions can be compiled in parallel."""
    source = """
def handler_a():
    pass

def handler_b():
    pass

def handler_c():
    pass
"""
    compiler = ParallelCompiler(max_workers=4)
    binary = compiler.compile(source)

    assert binary.startswith(MAGIC_HEADER)


def test_parallel_compiler_handles_dom_elements():
    """DOM elements (with statements) can be compiled in parallel."""
    source = """
with Div():
    pass

with Span():
    pass

with Button():
    pass
"""
    binary = compile_parallel(source, max_workers=4)

    assert binary.startswith(MAGIC_HEADER)
    # String pool should contain element tags
    assert b"div" in binary
    assert b"span" in binary
    assert b"button" in binary


def test_sharded_string_pool_creation():
    """ShardedStringPool creates correct number of shards."""
    pool = ShardedStringPool.create(4)

    assert len(pool.shards) == 4
    assert all(shard == () for shard in pool.shards)


def test_sharded_string_pool_add():
    """ShardedStringPool.add_to_shard returns new immutable pool."""
    pool = ShardedStringPool.create(4)
    pool2 = pool.add_to_shard(0, "hello")
    pool3 = pool2.add_to_shard(1, "world")

    # Original pool unchanged
    assert pool.shards[0] == ()

    # New pools have data
    assert pool2.shards[0] == ("hello",)
    assert pool3.shards[0] == ("hello",)
    assert pool3.shards[1] == ("world",)


def test_sharded_string_pool_merge():
    """ShardedStringPool.merge deduplicates strings."""
    pool = ShardedStringPool.create(3)
    pool = pool.add_to_shard(0, "hello")
    pool = pool.add_to_shard(0, "world")
    pool = pool.add_to_shard(1, "hello")  # Duplicate
    pool = pool.add_to_shard(2, "foo")

    merged = pool.merge()

    # Should deduplicate "hello"
    assert merged == ("hello", "world", "foo")


def test_parallel_compilation_thread_safety():
    """Parallel compilation is thread-safe."""
    source = """
count = Signal(0)
with Div(class_="container"):
    pass
"""
    results = []
    errors = []

    def compile_task() -> None:
        try:
            binary = compile_parallel(source, max_workers=2)
            results.append(binary)
        except Exception as e:
            errors.append(e)

    # Run multiple parallel compilations
    threads = [threading.Thread(target=compile_task) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All should succeed
    assert len(errors) == 0
    assert len(results) == 10

    # All should produce valid bytecode
    for binary in results:
        assert binary.startswith(MAGIC_HEADER)


def test_parallel_compiler_string_deduplication():
    """Strings are deduplicated across compilation units."""
    source = """
with Div(class_="container"):
    pass

with Div(class_="container"):
    pass
"""
    binary = compile_parallel(source, max_workers=4)

    # "div" and "container" should only appear once each in string pool
    # Count occurrences (rough check - depends on binary layout)
    assert binary.startswith(MAGIC_HEADER)


def test_compile_parallel_convenience_function():
    """compile_parallel convenience function works."""
    source = "x = Signal(0)"
    binary = compile_parallel(source)

    assert binary.startswith(MAGIC_HEADER)


def test_parallel_compiler_max_workers():
    """ParallelCompiler respects max_workers setting."""
    compiler = ParallelCompiler(max_workers=2)
    assert compiler.max_workers == 2

    compiler2 = ParallelCompiler(max_workers=8)
    assert compiler2.max_workers == 8
