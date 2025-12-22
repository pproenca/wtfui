"""Tests for inline counter example."""


def test_inline_counter_example_exists():
    """Inline counter example should exist and be importable."""
    import inline_counter

    assert hasattr(inline_counter, "Counter")
    assert hasattr(inline_counter, "_count")
    assert hasattr(inline_counter, "handle_key")


def test_inline_counter_app_runs():
    """Inline counter app should be callable."""
    from inline_counter import Counter

    # Should be able to call the component
    Counter()


def test_inline_counter_key_handler():
    """Key handler should modify shared state."""
    from inline_counter import _count, handle_key

    initial = _count.value
    handle_key("+")
    assert _count.value == initial + 1
    handle_key("-")
    assert _count.value == initial
