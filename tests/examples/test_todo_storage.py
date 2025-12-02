"""Tests for localStorage-like persistence."""

import tempfile
from pathlib import Path


def test_storage_set_and_get():
    from examples.todo.storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(Path(tmpdir) / "storage.json")
        storage.setItem("key", "value")
        assert storage.getItem("key") == "value"


def test_storage_persists_to_file():
    from examples.todo.storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "storage.json"
        storage1 = LocalStorage(path)
        storage1.setItem("todos", '[{"text": "Buy milk"}]')

        # New instance should read from file
        storage2 = LocalStorage(path)
        assert storage2.getItem("todos") == '[{"text": "Buy milk"}]'


def test_storage_remove_item():
    from examples.todo.storage import LocalStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(Path(tmpdir) / "storage.json")
        storage.setItem("key", "value")
        storage.removeItem("key")
        assert storage.getItem("key") is None
