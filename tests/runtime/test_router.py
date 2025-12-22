# tests/runtime/test_router.py
"""Tests for TUI Router with in-memory history."""

from wtfui.core.router import HistoryState


class TestHistoryStateNavigation:
    """Test HistoryState stack operations."""

    def test_initial_state_has_root_path(self) -> None:
        """New history starts at root path."""
        history = HistoryState()
        assert history.current_path == "/"

    def test_push_adds_to_stack(self) -> None:
        """push() adds path and moves cursor forward."""
        history = HistoryState()
        history.push("/users")
        assert history.current_path == "/users"

    def test_push_multiple_paths(self) -> None:
        """Multiple pushes build history stack."""
        history = HistoryState()
        history.push("/users")
        history.push("/users/123")
        assert history.current_path == "/users/123"
        assert len(history.stack) == 3  # /, /users, /users/123

    def test_back_moves_cursor(self) -> None:
        """back() moves to previous path."""
        history = HistoryState()
        history.push("/users")
        history.push("/settings")
        history.back()
        assert history.current_path == "/users"

    def test_back_at_root_stays_at_root(self) -> None:
        """back() at root doesn't go negative."""
        history = HistoryState()
        history.back()
        assert history.current_path == "/"
        assert history.cursor == 0

    def test_forward_after_back(self) -> None:
        """forward() restores path after back()."""
        history = HistoryState()
        history.push("/users")
        history.push("/settings")
        history.back()
        history.forward()
        assert history.current_path == "/settings"

    def test_forward_at_end_stays(self) -> None:
        """forward() at end of stack does nothing."""
        history = HistoryState()
        history.push("/users")
        history.forward()
        assert history.current_path == "/users"

    def test_push_after_back_truncates_stack(self) -> None:
        """push() after back() truncates forward history."""
        history = HistoryState()
        history.push("/a")
        history.push("/b")
        history.push("/c")
        history.back()
        history.back()
        # Now at /a, forward history is /b, /c
        history.push("/d")
        # Stack should be /, /a, /d (forward history truncated)
        assert history.stack == ["/", "/a", "/d"]
        assert history.current_path == "/d"


class TestHistoryStateSubscription:
    """Test reactive subscription to history changes."""

    def test_subscribe_receives_changes(self) -> None:
        """Subscribers receive path change notifications."""
        history = HistoryState()
        changes: list[str] = []
        history.subscribe(lambda path: changes.append(path))

        history.push("/users")
        assert changes == ["/users"]

    def test_unsubscribe_stops_notifications(self) -> None:
        """Unsubscribed callbacks are not called."""
        history = HistoryState()
        changes: list[str] = []
        unsub = history.subscribe(lambda path: changes.append(path))

        history.push("/a")
        unsub()
        history.push("/b")

        assert changes == ["/a"]  # /b not received

    def test_back_notifies_subscribers(self) -> None:
        """back() triggers subscriber notification."""
        history = HistoryState()
        changes: list[str] = []
        history.subscribe(lambda path: changes.append(path))

        history.push("/users")
        history.back()

        assert changes == ["/users", "/"]


class TestRouterMatching:
    """Test Router path matching."""

    def test_router_matches_exact_path(self) -> None:
        """Router returns component for exact path match."""
        from wtfui.core.router import Route, Router

        def home():
            return "Home"

        def users():
            return "Users"

        router = Router(
            [
                Route("/", home),
                Route("/users", users),
            ]
        )

        assert router.match("/") == home
        assert router.match("/users") == users

    def test_router_returns_none_for_no_match(self) -> None:
        """Router returns None when no path matches."""
        from wtfui.core.router import Route, Router

        router = Router(
            [
                Route("/", lambda: "Home"),
            ]
        )

        assert router.match("/unknown") is None

    def test_router_matches_path_params(self) -> None:
        """Router extracts path parameters."""
        from wtfui.core.router import Route, Router

        def user_detail(id: str):
            return f"User {id}"

        router = Router(
            [
                Route("/users/:id", user_detail),
            ]
        )

        component, params = router.match_with_params("/users/123")
        assert component is not None
        assert params == {"id": "123"}

    def test_router_matches_multiple_params(self) -> None:
        """Router extracts multiple path parameters."""
        from wtfui.core.router import Route, Router

        def item(user_id: str, item_id: str):
            return f"{user_id}/{item_id}"

        router = Router(
            [
                Route("/users/:user_id/items/:item_id", item),
            ]
        )

        _component, params = router.match_with_params("/users/42/items/99")
        assert params == {"user_id": "42", "item_id": "99"}


class TestRouterWithHistory:
    """Test Router integration with HistoryState."""

    def test_router_subscribes_to_history(self) -> None:
        """Router updates current route on history changes."""
        from wtfui.core.router import Route, Router

        history = HistoryState()
        router = Router(
            [
                Route("/", lambda: "Home"),
                Route("/users", lambda: "Users"),
            ]
        )
        router.bind_history(history)

        component = router.current_component()
        assert component is not None
        assert component() == "Home"

        history.push("/users")
        component = router.current_component()
        assert component is not None
        assert component() == "Users"


class TestNavigationKeyBindings:
    """Test keyboard navigation bindings."""

    def test_handle_key_alt_left_triggers_back(self) -> None:
        """Alt+Left triggers history.back()."""
        history = HistoryState()
        history.push("/users")
        history.push("/settings")

        # Simulate Alt+Left key
        from wtfui.core.router import handle_navigation_key

        handled = handle_navigation_key(history, key="left", alt=True)
        assert handled is True
        assert history.current_path == "/users"

    def test_handle_key_alt_right_triggers_forward(self) -> None:
        """Alt+Right triggers history.forward()."""
        history = HistoryState()
        history.push("/users")
        history.back()

        from wtfui.core.router import handle_navigation_key

        handled = handle_navigation_key(history, key="right", alt=True)
        assert handled is True
        assert history.current_path == "/users"

    def test_handle_key_without_alt_not_handled(self) -> None:
        """Arrow keys without Alt are not handled."""
        history = HistoryState()
        history.push("/users")

        from wtfui.core.router import handle_navigation_key

        handled = handle_navigation_key(history, key="left", alt=False)
        assert handled is False
        assert history.current_path == "/users"  # Unchanged
