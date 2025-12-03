"""Tests for compilation artifact cache.

Verifies that the cache correctly stores and retrieves
compiled bytecode with proper invalidation.
"""

import tempfile
import time
from pathlib import Path

from flow.compiler.cache import ArtifactCache, CacheEntry


def test_cache_creation():
    """ArtifactCache can be instantiated."""
    cache = ArtifactCache()
    assert len(cache) == 0


def test_cache_entry_slots():
    """CacheEntry uses __slots__ for memory efficiency."""
    entry = CacheEntry(
        source_hash="abc123",
        mtime=12345.0,
        bytecode=b"test",
    )

    assert hasattr(entry, "__slots__")
    assert entry.source_hash == "abc123"
    assert entry.mtime == 12345.0
    assert entry.bytecode == b"test"


def test_save_and_load():
    """Cache stores and retrieves bytecode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()
        bytecode = b"FLOW\x00\x01compiled"

        cache.save(source_file, bytecode)

        loaded = cache.load(source_file)
        assert loaded == bytecode


def test_is_valid_returns_true_for_cached():
    """is_valid returns True for valid cached entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()
        cache.save(source_file, b"compiled")

        assert cache.is_valid(source_file) is True


def test_is_valid_returns_false_for_uncached():
    """is_valid returns False for uncached file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()

        assert cache.is_valid(source_file) is False


def test_cache_invalidation_on_content_change():
    """Cache is invalidated when file content changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()
        cache.save(source_file, b"compiled_v1")

        # Change content
        time.sleep(0.01)  # Ensure mtime changes
        source_file.write_text("x = 2")

        # Cache should be invalid
        assert cache.is_valid(source_file) is False


def test_invalidate_removes_entry():
    """invalidate removes cache entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()
        cache.save(source_file, b"compiled")

        assert source_file in cache
        cache.invalidate(source_file)
        assert source_file not in cache


def test_clear_removes_all_entries():
    """clear removes all cache entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "a.py"
        file2 = Path(tmpdir) / "b.py"
        file1.write_text("a = 1")
        file2.write_text("b = 2")

        cache = ArtifactCache()
        cache.save(file1, b"a_compiled")
        cache.save(file2, b"b_compiled")

        assert len(cache) == 2
        cache.clear()
        assert len(cache) == 0


def test_persist_and_restore():
    """Cache can be persisted to disk and restored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")
        cache_dir = Path(tmpdir) / ".flowcache"

        # Save to cache
        cache1 = ArtifactCache()
        bytecode = b"FLOW\x00\x01persistent"
        cache1.save(source_file, bytecode)

        # Persist
        cache1.persist(cache_dir)

        # Restore to new cache
        cache2 = ArtifactCache()
        restored_count = cache2.restore(cache_dir)

        assert restored_count == 1
        assert cache2.load(source_file) == bytecode


def test_stats():
    """stats returns cache statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "a.py"
        file2 = Path(tmpdir) / "b.py"
        file1.write_text("a = 1")
        file2.write_text("b = 2")

        cache = ArtifactCache()
        cache.save(file1, b"a_bytecode")
        cache.save(file2, b"bb_bytecode")

        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["total_bytes"] == len(b"a_bytecode") + len(b"bb_bytecode")


def test_load_returns_none_for_uncached():
    """load returns None for uncached file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()

        assert cache.load(source_file) is None


def test_contains_operator():
    """in operator checks if path is cached."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = Path(tmpdir) / "app.py"
        source_file.write_text("x = 1")

        cache = ArtifactCache()
        assert source_file not in cache

        cache.save(source_file, b"compiled")
        assert source_file in cache


def test_restore_from_nonexistent_dir():
    """restore handles nonexistent directory gracefully."""
    cache = ArtifactCache()
    restored = cache.restore(Path("/nonexistent/path"))
    assert restored == 0


def test_restore_from_invalid_index():
    """restore handles invalid index file gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        (cache_dir / "index.json").write_text("not valid json{")

        cache = ArtifactCache()
        restored = cache.restore(cache_dir)
        assert restored == 0


def test_multiple_files_caching():
    """Cache handles multiple files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i in range(5):
            f = Path(tmpdir) / f"module_{i}.py"
            f.write_text(f"x = {i}")
            files.append(f)

        cache = ArtifactCache()
        for i, f in enumerate(files):
            cache.save(f, f"bytecode_{i}".encode())

        assert len(cache) == 5

        for i, f in enumerate(files):
            assert cache.load(f) == f"bytecode_{i}".encode()
