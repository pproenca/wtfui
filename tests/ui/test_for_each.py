"""Tests for the reactive For component."""

import pytest

from wtfui import Signal
from wtfui.ui.elements import Div, Text


class TestForBasic:
    """Basic For component functionality."""

    @pytest.mark.asyncio
    async def test_for_renders_initial_items(self):
        """For renders all initial list items."""
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.ui.for_each import For

        items = Signal(["a", "b", "c"])

        # Create parent container
        parent = Div()

        # Render For inside parent
        token = set_current_parent(parent)
        try:
            for_elem = For(
                each=items,
                render=lambda item, idx: Text(item),
            )
        finally:
            reset_parent(token)

        # For should have 3 children (one per item)
        assert len(for_elem.children) == 3

    @pytest.mark.asyncio
    async def test_for_adds_items_when_signal_changes(self):
        """For adds new children when items are added to Signal."""
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.tui.testing import stabilize
        from wtfui.ui.for_each import For

        items = Signal(["a"])

        parent = Div()
        token = set_current_parent(parent)
        try:
            for_elem = For(each=items, render=lambda item, idx: Text(item))
        finally:
            reset_parent(token)

        assert len(for_elem.children) == 1

        # Add items to signal
        items.value = ["a", "b", "c"]
        await stabilize()

        # For should now have 3 children
        assert len(for_elem.children) == 3

    @pytest.mark.asyncio
    async def test_for_removes_items_when_signal_changes(self):
        """For removes children when items are removed from Signal."""
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.tui.testing import stabilize
        from wtfui.ui.for_each import For

        items = Signal(["a", "b", "c"])

        parent = Div()
        token = set_current_parent(parent)
        try:
            for_elem = For(each=items, render=lambda item, idx: Text(item))
        finally:
            reset_parent(token)

        assert len(for_elem.children) == 3

        # Remove items
        items.value = ["b"]
        await stabilize()

        # For should now have 1 child
        assert len(for_elem.children) == 1


class TestForKeyedReuse:
    """For reuses elements by key."""

    @pytest.mark.asyncio
    async def test_for_reuses_elements_by_key(self):
        """Elements with same key are reused across updates."""
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.tui.testing import stabilize
        from wtfui.ui.for_each import For

        items = Signal([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])

        parent = Div()
        token = set_current_parent(parent)
        try:
            for_elem = For(
                each=items,
                render=lambda item, idx: Text(item["name"]),
                key=lambda x: x["id"],
            )
        finally:
            reset_parent(token)

        # Capture element references
        first_child = for_elem.children[0]
        second_child = for_elem.children[1]

        # Reorder items (swap positions)
        items.value = [{"id": 2, "name": "b"}, {"id": 1, "name": "a"}]
        await stabilize()

        # Elements should be reused (same instances, different order)
        assert for_elem.children[0] is second_child
        assert for_elem.children[1] is first_child


class TestForWithComputed:
    """For works with Computed sources."""

    @pytest.mark.asyncio
    async def test_for_with_computed_source(self):
        """For updates when underlying Computed changes."""
        from wtfui.core.computed import Computed
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.tui.testing import stabilize
        from wtfui.ui.for_each import For

        base = Signal([1, 2, 3, 4, 5])
        filtered = Computed(lambda: [x for x in base.value if x > 2])

        parent = Div()
        token = set_current_parent(parent)
        try:
            for_elem = For(each=filtered, render=lambda item, idx: Text(str(item)))
        finally:
            reset_parent(token)

        # Initial: [3, 4, 5]
        assert len(for_elem.children) == 3

        # Update base signal to change computed result
        base.value = [1, 2]  # Filtered: []
        await stabilize()

        assert len(for_elem.children) == 0


class TestForDispose:
    """For cleanup and disposal."""

    @pytest.mark.asyncio
    async def test_for_dispose_stops_updates(self):
        """Disposed For doesn't update on Signal changes."""
        from wtfui.core.context import reset_parent, set_current_parent
        from wtfui.tui.testing import stabilize
        from wtfui.ui.for_each import For

        items = Signal(["a"])

        parent = Div()
        token = set_current_parent(parent)
        try:
            for_elem = For(each=items, render=lambda item, idx: Text(item))
        finally:
            reset_parent(token)

        assert len(for_elem.children) == 1

        # Dispose
        for_elem.dispose()

        # Change signal (should not affect disposed For)
        items.value = ["a", "b", "c"]
        await stabilize()

        # Should still have 1 child (no update)
        assert len(for_elem.children) == 1
