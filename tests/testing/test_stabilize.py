"""Tests for the stabilize testing utility."""

import pytest

from wtfui.core.effect import Effect
from wtfui.core.scheduler import reset_scheduler
from wtfui.core.signal import Signal


class TestStabilize:
    """Test the stabilize() function for waiting on effects."""

    @pytest.mark.asyncio
    async def test_stabilize_waits_for_effects(self):
        """stabilize() should wait until all scheduled effects complete."""
        from wtfui.tui.testing import stabilize

        results = []
        signal = Signal(0)

        def track_effect():
            results.append(signal.value)

        effect = Effect(track_effect)

        # Trigger signal change (schedules effect)
        signal.value = 1
        signal.value = 2

        # Wait for effects to complete
        await stabilize()

        # Effect should have run (at least once, possibly multiple times)
        assert len(results) > 0
        assert 2 in results  # Final value should be tracked

        effect.dispose()
        reset_scheduler()

    @pytest.mark.asyncio
    async def test_stabilize_with_max_wait(self):
        """stabilize() should accept a max_wait parameter."""
        from wtfui.tui.testing import stabilize

        # Should not raise with reasonable max_wait
        result = await stabilize(max_wait=0.5)
        assert result is True

    @pytest.mark.asyncio
    async def test_stabilize_returns_true_when_idle(self):
        """stabilize() returns True when scheduler is idle."""
        from wtfui.tui.testing import stabilize

        # No pending effects
        result = await stabilize()
        assert result is True
