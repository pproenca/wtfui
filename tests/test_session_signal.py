"""Tests for SessionSignal (React 19-style per-client state isolation)."""

from wtfui.core.signal import SessionSignal
from wtfui.web.server.app import SessionState, set_current_session


class TestSessionSignal:
    """Tests for SessionSignal behavior."""

    def test_session_signal_uses_default_without_session(self) -> None:
        """Without a session context, SessionSignal uses default value."""
        sig = SessionSignal("default", name="test1")
        assert sig.value == "default"

    def test_session_signal_stores_in_session(self) -> None:
        """With a session context, SessionSignal stores in session."""
        session = SessionState()
        set_current_session(session)
        try:
            sig = SessionSignal("default", name="test2")
            sig.value = "updated"
            assert sig.value == "updated"
            assert session.signal_values["test2"] == "updated"
        finally:
            set_current_session(None)

    def test_session_signal_isolation_between_sessions(self) -> None:
        """Different sessions have isolated signal values."""
        sig = SessionSignal("default", name="shared_name")

        session_a = SessionState()
        session_b = SessionState()

        # Set value in session A
        set_current_session(session_a)
        sig.value = "user_a_value"
        assert sig.value == "user_a_value"

        # Switch to session B - should see default
        set_current_session(session_b)
        assert sig.value == "default"  # B hasn't set a value

        # Set value in session B
        sig.value = "user_b_value"
        assert sig.value == "user_b_value"

        # Switch back to session A - should see A's value
        set_current_session(session_a)
        assert sig.value == "user_a_value"

        set_current_session(None)

    def test_session_signal_notifies_subscribers(self) -> None:
        """SessionSignal notifies subscribers on change."""
        session = SessionState()
        set_current_session(session)
        try:
            sig = SessionSignal(0, name="test3")
            notifications = []
            sig.subscribe(lambda: notifications.append(sig.value))

            sig.value = 1
            sig.value = 2

            assert notifications == [1, 2]
        finally:
            set_current_session(None)

    def test_session_signal_no_notify_same_value(self) -> None:
        """SessionSignal doesn't notify on same value."""
        session = SessionState()
        set_current_session(session)
        try:
            sig = SessionSignal(0, name="test4")
            notifications = []
            sig.subscribe(lambda: notifications.append(sig.value))

            sig.value = 0  # Same as default
            assert notifications == []
        finally:
            set_current_session(None)

    def test_session_signal_repr(self) -> None:
        """SessionSignal has informative repr."""
        sig = SessionSignal("hello", name="myname")
        assert "SessionSignal" in repr(sig)
        assert "hello" in repr(sig)
        assert "myname" in repr(sig)
