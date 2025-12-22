"""Tests for greenlet contamination guard."""

import warnings


def test_greenlet_not_installed_no_warning():
    """When greenlet is not installed, no warning is issued."""
    from wtfui.core._greenlet_guard import check_greenlet_contamination

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_greenlet_contamination()

    greenlet_warnings = [x for x in w if "greenlet" in str(x.message).lower()]
    assert len(greenlet_warnings) == 0


def test_greenlet_installed_emits_warning(monkeypatch):
    """When greenlet is installed, a warning is emitted."""
    # Mock greenlet being importable
    import sys
    from types import ModuleType

    fake_greenlet = ModuleType("greenlet")
    monkeypatch.setitem(sys.modules, "greenlet", fake_greenlet)

    # Clear any cached check
    import importlib

    import wtfui.core._greenlet_guard as guard_module

    importlib.reload(guard_module)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        guard_module.check_greenlet_contamination()

    greenlet_warnings = [x for x in w if "greenlet" in str(x.message).lower()]
    assert len(greenlet_warnings) == 1
    assert "GIL" in str(greenlet_warnings[0].message)


def test_greenlet_error_mode_via_env(monkeypatch):
    """WTFUI_GREENLET_ERROR=1 raises instead of warning."""
    import sys
    from types import ModuleType

    fake_greenlet = ModuleType("greenlet")
    monkeypatch.setitem(sys.modules, "greenlet", fake_greenlet)
    monkeypatch.setenv("WTFUI_GREENLET_ERROR", "1")

    import importlib

    import wtfui.core._greenlet_guard as guard_module

    importlib.reload(guard_module)

    import pytest

    from wtfui.core._greenlet_guard import GreenletContaminationError

    with pytest.raises(GreenletContaminationError):
        guard_module.check_greenlet_contamination()
