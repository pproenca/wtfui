"""Test Signal can be imported from wtfui.core."""


def test_signal_import_from_core():
    """Signal should be importable from wtfui.core."""
    from wtfui.core import Signal

    assert Signal is not None


def test_signal_basic_from_core():
    """Signal from core should work identically to wtfui.signal."""
    from wtfui.core import Signal

    sig = Signal(42)
    assert sig.value == 42

    sig.value = 100
    assert sig.value == 100
