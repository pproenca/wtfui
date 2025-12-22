"""Tests for localStorage-like persistence."""

import tempfile
from pathlib import Path


def test_storage_set_and_get():
    from storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(Path(tmpdir) / "storage.json")
        storage.set_item("key", "value")
        assert storage.get_item("key") == "value"


def test_storage_persists_to_file():
    from storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "storage.json"
        storage1 = LocalStorage(path)
        storage1.set_item("todos", '[{"text": "Buy milk"}]')

        # New instance should read from file
        storage2 = LocalStorage(path)
        assert storage2.get_item("todos") == '[{"text": "Buy milk"}]'


def test_storage_remove_item():
    from storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(Path(tmpdir) / "storage.json")
        storage.set_item("key", "value")
        storage.remove_item("key")
        assert storage.get_item("key") is None
