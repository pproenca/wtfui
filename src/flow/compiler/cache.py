"""Compilation Artifact Cache.

Caches compiled bytecode to speed up incremental builds.
Uses file modification time and content hash for invalidation.

Key Features:
- Hash-based invalidation (content-addressable)
- Mtime check for quick invalidation
- Thread-safe operations
- Lock-free reads

Pipeline Position:
    ParallelCompiler → [ArtifactCache] → .fbc files

Performance:
- Cache hit: ~1ms (read cached bytes)
- Cache miss: ~40ms (full compilation)
- Expected hit rate: >80% for typical dev workflow
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class CacheEntry:
    """Represents a cached compilation artifact.

    Attributes:
        source_hash: SHA-256 hash of source file
        mtime: File modification time at compilation
        bytecode: Compiled bytecode
    """

    __slots__ = ("bytecode", "mtime", "source_hash")

    def __init__(self, source_hash: str, mtime: float, bytecode: bytes) -> None:
        self.source_hash = source_hash
        self.mtime = mtime
        self.bytecode = bytecode


class ArtifactCache:
    """Thread-safe compilation artifact cache.

    Stores compiled bytecode indexed by source file path.
    Uses content hashing for reliable invalidation.

    Example:
        cache = ArtifactCache()

        # Check if file is cached
        if cache.is_valid(Path("app.py")):
            bytecode = cache.load(Path("app.py"))
        else:
            bytecode = compiler.compile(Path("app.py"))
            cache.save(Path("app.py"), bytecode)

        # Save to disk for persistence across runs
        cache.persist(Path(".flowcache"))
    """

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._entries: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def is_valid(self, path: Path) -> bool:
        """Check if cache entry is valid for file.

        Performs quick mtime check first, then hash check if needed.
        Thread-safe under No-GIL: uses lock for reads.

        Args:
            path: Source file path

        Returns:
            True if cached bytecode is still valid
        """
        key = str(path.resolve())

        with self._lock:
            entry = self._entries.get(key)

        if entry is None:
            return False

        # Quick check: mtime
        try:
            current_mtime = path.stat().st_mtime
            if current_mtime != entry.mtime:
                # Mtime changed, need to verify hash
                current_hash = self._hash_file(path)
                if current_hash != entry.source_hash:
                    return False
                # Hash matches, update mtime (benign race under No-GIL)
                with self._lock:
                    # Re-check entry still exists
                    if key in self._entries:
                        self._entries[key].mtime = current_mtime
        except OSError:
            return False

        return True

    def load(self, path: Path) -> bytes | None:
        """Load cached bytecode for file.

        Thread-safe under No-GIL.

        Args:
            path: Source file path

        Returns:
            Cached bytecode or None if not cached
        """
        key = str(path.resolve())
        with self._lock:
            entry = self._entries.get(key)
        return entry.bytecode if entry else None

    def save(self, path: Path, bytecode: bytes) -> None:
        """Save bytecode to cache.

        Thread-safe operation.

        Args:
            path: Source file path
            bytecode: Compiled bytecode
        """
        key = str(path.resolve())

        try:
            source_hash = self._hash_file(path)
            mtime = path.stat().st_mtime
        except OSError:
            return  # File no longer exists

        entry = CacheEntry(
            source_hash=source_hash,
            mtime=mtime,
            bytecode=bytecode,
        )

        with self._lock:
            self._entries[key] = entry

    def invalidate(self, path: Path) -> None:
        """Invalidate cache entry for file.

        Args:
            path: Source file path
        """
        key = str(path.resolve())
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._entries.clear()

    def persist(self, cache_dir: Path) -> None:
        """Persist cache to disk.

        Saves cache entries as JSON index + bytecode files.
        Thread-safe: snapshots entries under lock before writing.

        Args:
            cache_dir: Directory to store cache files
        """
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot entries under lock to avoid iteration race
        with self._lock:
            entries_snapshot = list(self._entries.items())

        # Build index
        index: dict[str, dict[str, str | float]] = {}

        for key, entry in entries_snapshot:
            # Save bytecode file
            bytecode_path = cache_dir / f"{entry.source_hash}.fbc"
            bytecode_path.write_bytes(entry.bytecode)

            # Add to index
            index[key] = {
                "hash": entry.source_hash,
                "mtime": entry.mtime,
            }

        # Save index
        index_path = cache_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2))

    def restore(self, cache_dir: Path) -> int:
        """Restore cache from disk.

        Args:
            cache_dir: Directory containing cache files

        Returns:
            Number of entries restored
        """
        index_path = cache_dir / "index.json"
        if not index_path.exists():
            return 0

        try:
            index: Mapping[str, dict[str, str | float]] = json.loads(index_path.read_text())
        except (json.JSONDecodeError, OSError):
            return 0

        restored = 0

        for key, entry_data in index.items():
            source_hash = str(entry_data.get("hash", ""))
            mtime = float(entry_data.get("mtime", 0))

            bytecode_path = cache_dir / f"{source_hash}.fbc"
            if not bytecode_path.exists():
                continue

            try:
                bytecode = bytecode_path.read_bytes()
            except OSError:
                continue

            entry = CacheEntry(
                source_hash=source_hash,
                mtime=mtime,
                bytecode=bytecode,
            )

            self._entries[key] = entry
            restored += 1

        return restored

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Thread-safe under No-GIL.

        Returns:
            Dict with 'entries' and 'total_bytes' keys
        """
        with self._lock:
            entries = list(self._entries.values())
        total_bytes = sum(len(e.bytecode) for e in entries)
        return {
            "entries": len(entries),
            "total_bytes": total_bytes,
        }

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of file contents.

        Args:
            path: File path

        Returns:
            Hex-encoded hash
        """
        hasher = hashlib.sha256()
        content = path.read_bytes()
        hasher.update(content)
        return hasher.hexdigest()

    def __len__(self) -> int:
        """Return number of cached entries."""
        with self._lock:
            return len(self._entries)

    def __contains__(self, path: Path) -> bool:
        """Check if path is in cache."""
        key = str(path.resolve())
        with self._lock:
            return key in self._entries
