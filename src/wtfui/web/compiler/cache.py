import hashlib
import json
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class CacheEntry:
    __slots__ = ("bytecode", "mtime", "source_hash")

    def __init__(self, source_hash: str, mtime: float, bytecode: bytes) -> None:
        self.source_hash = source_hash
        self.mtime = mtime
        self.bytecode = bytecode


class ArtifactCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def is_valid(self, path: Path) -> bool:
        key = str(path.resolve())

        with self._lock:
            entry = self._entries.get(key)

        if entry is None:
            return False

        try:
            current_mtime = path.stat().st_mtime
            if current_mtime != entry.mtime:
                current_hash = self._hash_file(path)
                if current_hash != entry.source_hash:
                    return False

                with self._lock:
                    if key in self._entries:
                        self._entries[key].mtime = current_mtime
        except OSError:
            return False

        return True

    def load(self, path: Path) -> bytes | None:
        key = str(path.resolve())
        with self._lock:
            entry = self._entries.get(key)
        return entry.bytecode if entry else None

    def save(self, path: Path, bytecode: bytes) -> None:
        key = str(path.resolve())

        try:
            source_hash = self._hash_file(path)
            mtime = path.stat().st_mtime
        except OSError:
            return

        entry = CacheEntry(
            source_hash=source_hash,
            mtime=mtime,
            bytecode=bytecode,
        )

        with self._lock:
            self._entries[key] = entry

    def invalidate(self, path: Path) -> None:
        key = str(path.resolve())
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def persist(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            entries_snapshot = list(self._entries.items())

        index: dict[str, dict[str, str | float]] = {}

        for key, entry in entries_snapshot:
            bytecode_path = cache_dir / f"{entry.source_hash}.mfbc"
            bytecode_path.write_bytes(entry.bytecode)

            index[key] = {
                "hash": entry.source_hash,
                "mtime": entry.mtime,
            }

        index_path = cache_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2))

    def restore(self, cache_dir: Path) -> int:
        index_path = cache_dir / "index.json"
        if not index_path.exists():
            return 0

        try:
            index: Mapping[str, dict[str, str | float]] = json.loads(index_path.read_text())
        except json.JSONDecodeError, OSError:
            return 0

        restored = 0

        for key, entry_data in index.items():
            source_hash = str(entry_data.get("hash", ""))
            mtime = float(entry_data.get("mtime", 0))

            bytecode_path = cache_dir / f"{source_hash}.mfbc"
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
        with self._lock:
            entries = list(self._entries.values())
        total_bytes = sum(len(e.bytecode) for e in entries)
        return {
            "entries": len(entries),
            "total_bytes": total_bytes,
        }

    def _hash_file(self, path: Path) -> str:
        hasher = hashlib.sha256()
        content = path.read_bytes()
        hasher.update(content)
        return hasher.hexdigest()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, path: Path) -> bool:
        key = str(path.resolve())
        with self._lock:
            return key in self._entries
