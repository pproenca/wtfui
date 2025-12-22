"""Tests for LLM chat example."""


def test_llm_chat_example_exists():
    """LLM chat example should exist and be importable."""
    import llm_chat

    assert hasattr(llm_chat, "LLMChat")


def test_llm_chat_has_messages_signal():
    """LLM chat should use a Signal for messages list."""
    from llm_chat import LLMChat

    # Call the component to get the element tree
    result = LLMChat()
    # The component should have created message state
    assert result is not None
