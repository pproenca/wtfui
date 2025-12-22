"""Tests for style manifest resolution in ConsoleRenderer."""

from wtfui.tui.renderer.cell import Cell
from wtfui.tui.renderer.manifest import StyleManifest
from wtfui.tui.renderer.theme import apply_cls_to_cell


def test_manifest_loads_json() -> None:
    """StyleManifest loads from JSON dict."""
    data = {"fl-abc123": {"background-color": "#3b82f6", "color": "#ffffff"}}
    manifest = StyleManifest(data)

    assert manifest.resolve("fl-abc123") == {"background-color": "#3b82f6", "color": "#ffffff"}


def test_manifest_returns_none_for_unknown() -> None:
    """Unknown classes return None."""
    manifest = StyleManifest({})
    assert manifest.resolve("fl-unknown") is None


def test_apply_cls_resolves_atomic_class() -> None:
    """apply_cls_to_cell resolves fl-* classes via manifest."""
    from wtfui.tui.renderer import manifest as manifest_module

    # Set up manifest
    manifest_module._global_manifest = StyleManifest({"fl-test": {"background-color": "#ff0000"}})

    cell = Cell(char="X")
    apply_cls_to_cell(cell, "fl-test")

    # Red background: (255, 0, 0)
    assert cell.bg == (255, 0, 0)
