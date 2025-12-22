"""Test Effect and Computed can be imported from wtfui.core."""


def test_effect_import_from_core():
    """Effect should be importable from wtfui.core."""
    from wtfui.core import Effect

    assert Effect is not None


def test_computed_import_from_core():
    """Computed should be importable from wtfui.core."""
    from wtfui.core import Computed

    assert Computed is not None


def test_effect_tracks_signal():
    """Effect from core should track Signal dependencies."""
    from wtfui.core import Effect, Signal, wait_for_scheduler

    count = Signal(0)
    observed = []

    def track():
        observed.append(count.value)

    Effect(track)
    assert observed == [0]

    count.value = 1
    wait_for_scheduler()
    assert observed == [0, 1]


def test_computed_derives_value():
    """Computed from core should derive values from Signals."""
    from wtfui.core import Computed, Signal

    base = Signal(5)
    doubled = Computed(lambda: base.value * 2)

    assert doubled() == 10

    base.value = 7
    assert doubled() == 14
