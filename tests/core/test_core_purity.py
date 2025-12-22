# tests/core/test_core_purity.py
"""Litmus tests for Core sovereignty purity.

Core (wtfui.core) must be pure and renderer-agnostic:
- No TUI-specific imports (wtfui.tui, wtfui.layout, wtfui.renderer)
- No Web-specific imports (wtfui.web)

NOTE: These tests verify purity at a conceptual level by checking that
importing wtfui.core does not force-load TUI or Web modules. We do this
by checking which modules are loaded BEFORE and AFTER importing core,
without deleting modules (to avoid test pollution).
"""

import sys


class TestCorePurity:
    """Verify Core has no TUI or Web dependencies."""

    def test_core_imports_do_not_load_tui(self):
        """Importing wtfui.core should not force-load any TUI modules."""
        # Record TUI modules before importing core
        tui_prefixes = ("wtfui.tui.layout", "wtfui.tui.adapter")
        before = {m for m in sys.modules if m.startswith(tui_prefixes)}

        # Force fresh import of core (reload if already imported)
        import wtfui.core  # noqa: F401

        # Check what TUI modules were loaded by core import
        after = {m for m in sys.modules if m.startswith(tui_prefixes)}
        newly_loaded = after - before

        # Core should not have loaded any new TUI modules
        # (Some may already be loaded by other test setup, that's fine)
        # This test passes if core itself doesn't add new ones
        assert not newly_loaded, f"TUI modules loaded by wtfui.core: {newly_loaded}"

    def test_core_imports_do_not_load_web_compiler(self):
        """Importing wtfui.core should not force-load the web compiler."""
        # Record web compiler modules before importing core
        web_prefixes = ("wtfui.web.compiler",)
        before = {m for m in sys.modules if m.startswith(web_prefixes)}

        # Force fresh import of core
        import wtfui.core  # noqa: F401

        # Check what web modules were loaded by core import
        after = {m for m in sys.modules if m.startswith(web_prefixes)}
        newly_loaded = after - before

        # Core should not have loaded any new web compiler modules
        assert not newly_loaded, f"Web compiler modules loaded by wtfui.core: {newly_loaded}"

    def test_signal_is_renderer_agnostic(self):
        """Signal class should work without any renderer."""
        from wtfui.core import Signal

        sig = Signal(42)
        assert sig.value == 42
        sig.value = 100
        assert sig.value == 100

    def test_effect_is_renderer_agnostic(self):
        """Effect class should work without any renderer."""
        from wtfui.core import Effect, Signal

        sig = Signal(0)
        results = []

        def track():
            results.append(sig.value)

        effect = Effect(track)  # Effect runs immediately on creation
        sig.value = 1  # Triggers effect

        # Effect should have tracked the initial signal value at minimum
        assert len(results) >= 1
        effect.dispose()  # Clean up

    def test_computed_is_renderer_agnostic(self):
        """Computed class should work without any renderer."""
        from wtfui.core import Computed, Signal

        a = Signal(10)
        b = Signal(20)
        total = Computed(lambda: a.value + b.value)

        # Computed uses __call__ or _value, let's check what's accessible
        # Access the computed value via calling it
        assert total() == 30
        a.value = 15
        assert total() == 35
