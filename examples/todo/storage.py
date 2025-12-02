"""localStorage-like API with file persistence."""

from __future__ import annotations

import json
from pathlib import Path


class LocalStorage:
    """Browser localStorage-like API backed by JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".flow" / "todo_storage.json"
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load data from file if it exists."""
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        """Persist data to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data))

    def getItem(self, key: str) -> str | None:
        """Get item by key, returns None if not found."""
        return self._data.get(key)

    def setItem(self, key: str, value: str) -> None:
        """Set item and persist to file."""
        self._data[key] = value
        self._save()

    def removeItem(self, key: str) -> None:
        """Remove item by key."""
        self._data.pop(key, None)
        self._save()

    def clear(self) -> None:
        """Clear all items."""
        self._data.clear()
        self._save()
