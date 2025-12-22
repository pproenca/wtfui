"""Tests for todo app input validation."""


class TestTodoValidation:
    """Test suite for todo input validation."""

    def setup_method(self):
        """Reset state before each test."""
        from app import _new_todo_text, _todos

        _todos.value = []
        _new_todo_text.value = ""

    def test_add_valid_todo(self):
        """Verify valid todos are added."""
        from app import _new_todo_text, _todos, add_todo

        _new_todo_text.value = "Buy groceries"
        add_todo()

        assert len(_todos.value) == 1
        assert _todos.value[0].text == "Buy groceries"

    def test_add_todo_strips_whitespace(self):
        """Verify whitespace is stripped from todo text."""
        from app import _new_todo_text, _todos, add_todo

        _new_todo_text.value = "  Clean house  "
        add_todo()

        assert len(_todos.value) == 1
        assert _todos.value[0].text == "Clean house"

    def test_add_todo_rejects_empty(self):
        """Verify empty text is rejected."""
        from app import _new_todo_text, _todos, add_todo

        _new_todo_text.value = ""
        add_todo()

        assert len(_todos.value) == 0

    def test_add_todo_rejects_whitespace_only(self):
        """Verify whitespace-only text is rejected."""
        from app import _new_todo_text, _todos, add_todo

        _new_todo_text.value = "   \t\n   "
        add_todo()

        assert len(_todos.value) == 0

    def test_add_todo_rejects_too_long(self):
        """Verify text over _MAX_TODO_LENGTH is rejected."""
        from app import _MAX_TODO_LENGTH, _new_todo_text, _todos, add_todo

        _new_todo_text.value = "x" * (_MAX_TODO_LENGTH + 1)
        add_todo()

        assert len(_todos.value) == 0

    def test_add_todo_accepts_max_length(self):
        """Verify text at exactly _MAX_TODO_LENGTH is accepted."""
        from app import _MAX_TODO_LENGTH, _new_todo_text, _todos, add_todo

        _new_todo_text.value = "x" * _MAX_TODO_LENGTH
        add_todo()

        assert len(_todos.value) == 1
