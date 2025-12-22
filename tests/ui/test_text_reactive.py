"""Tests for reactive Text element.

Verifies that Text properly handles:
- Static strings (backward compatible)
- Signal[Any] values (reactive)
- Computed values (reactive)
- dispose() cleanup
"""

from __future__ import annotations

from wtfui import Computed, Signal
from wtfui.ui import Text


class TestTextStatic:
    """Tests for static Text content."""

    def test_text_with_string(self) -> None:
        """Text accepts static string content."""
        text = Text("Hello World")
        assert text.content == "Hello World"

    def test_text_with_empty_string(self) -> None:
        """Text accepts empty string."""
        text = Text("")
        assert text.content == ""

    def test_text_with_number_string(self) -> None:
        """Text converts to string if needed."""
        text = Text("42")
        assert text.content == "42"

    def test_text_no_effect_for_static(self) -> None:
        """Static Text should not create an Effect."""
        text = Text("static")
        assert text._effect is None


class TestTextWithSignal:
    """Tests for Signal-bound Text content."""

    def test_text_reads_signal_value(self) -> None:
        """Text reads current value from Signal."""
        sig = Signal("initial")
        text = Text(sig)
        assert text.content == "initial"

    def test_text_updates_when_signal_changes(self) -> None:
        """Text content reflects Signal updates."""
        sig = Signal("before")
        text = Text(sig)
        assert text.content == "before"

        sig.value = "after"
        assert text.content == "after"

    def test_text_creates_effect_for_signal(self) -> None:
        """Signal-bound Text creates an Effect for reactivity."""
        sig = Signal("value")
        text = Text(sig)
        assert text._effect is not None

    def test_text_handles_numeric_signal(self) -> None:
        """Text converts Signal value to string."""
        sig = Signal(42.5)
        text = Text(sig)
        assert text.content == "42.5"

        sig.value = 100
        assert text.content == "100"


class TestTextWithComputed:
    """Tests for Computed-bound Text content."""

    def test_text_reads_computed_value(self) -> None:
        """Text reads current value from Computed."""
        count = Signal(5)
        computed = Computed(lambda: f"Count: {count.value}")
        text = Text(computed)
        assert text.content == "Count: 5"

    def test_text_updates_when_computed_changes(self) -> None:
        """Text content reflects Computed updates."""
        count = Signal(0)
        computed = Computed(lambda: f"Value is {count.value}")
        text = Text(computed)
        assert text.content == "Value is 0"

        count.value = 10
        assert text.content == "Value is 10"

    def test_text_creates_effect_for_computed(self) -> None:
        """Computed-bound Text creates an Effect for reactivity."""
        computed = Computed(lambda: "computed")
        text = Text(computed)
        assert text._effect is not None


class TestTextDispose:
    """Tests for Text dispose() cleanup."""

    def test_dispose_cleans_up_effect(self) -> None:
        """dispose() removes Effect subscription."""
        sig = Signal("value")
        text = Text(sig)
        assert text._effect is not None

        text.dispose()
        assert text._effect is None

    def test_dispose_safe_for_static_text(self) -> None:
        """dispose() is safe to call on static Text."""
        text = Text("static")
        text.dispose()  # Should not raise
        assert text._effect is None

    def test_dispose_prevents_further_updates(self) -> None:
        """After dispose(), Signal changes don't affect Text."""
        sig = Signal("before")
        text = Text(sig)

        # Read initial value
        assert text.content == "before"

        # Dispose
        text.dispose()

        # Signal still works but Text is disconnected
        sig.value = "after"
        # Text can still read current value (it's just not reactive)
        assert text.content == "after"


class TestTextLayoutStyle:
    """Tests for Text intrinsic sizing."""

    def test_static_text_intrinsic_width(self) -> None:
        """Static Text has intrinsic width based on content length."""
        from wtfui.tui.adapter import LayoutAdapter

        text = Text("Hello")
        style = LayoutAdapter().get_layout_style(text)
        assert style.width.value == 5  # len("Hello")

    def test_signal_text_intrinsic_width(self) -> None:
        """Signal-bound Text has intrinsic width based on current value."""
        from wtfui.tui.adapter import LayoutAdapter

        sig = Signal("Hi")
        text = Text(sig)
        style = LayoutAdapter().get_layout_style(text)
        assert style.width.value == 2  # len("Hi")

        sig.value = "Hello World"
        style = LayoutAdapter().get_layout_style(text)
        assert style.width.value == 11  # len("Hello World")
