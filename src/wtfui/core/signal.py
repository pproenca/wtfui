import threading
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.computed import Computed
    from wtfui.core.effect import Effect


class Signal[T]:
    __slots__ = ("_computeds", "_effects", "_lock", "_subscribers", "_value")

    def __init__(self, value: T) -> None:
        self._value = value
        self._subscribers = set()
        self._effects = set()
        self._computeds = set()
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        from wtfui.core.computed import get_evaluating_computed
        from wtfui.core.effect import get_running_effect

        effect = get_running_effect()
        computed = get_evaluating_computed()

        with self._lock:
            if effect is not None:
                self._effects.add(effect)
            if computed is not None:
                self._computeds.add(computed)
            val = self._value

        if effect is not None:
            effect._track_signal(self)
        if computed is not None:
            computed._track_signal(self)

        return val

    @value.setter
    def value(self, new_value: T) -> None:
        subscribers_to_notify = []
        effects_to_schedule = []
        computeds_to_invalidate = []

        with self._lock:
            if self._value != new_value:
                self._value = new_value

                subscribers_to_notify = list(self._subscribers)
                effects_to_schedule = list(self._effects)
                computeds_to_invalidate = list(self._computeds)

        for subscriber in subscribers_to_notify:
            subscriber()

        for effect in effects_to_schedule:
            effect.schedule()

        for computed in computeds_to_invalidate:
            computed.invalidate()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._subscribers.discard(callback)

    def _remove_effect(self, effect: Effect) -> None:
        with self._lock:
            self._effects.discard(effect)

    def _remove_computed(self, computed: Computed[Any]) -> None:
        with self._lock:
            self._computeds.discard(computed)

    def __repr__(self) -> str:
        with self._lock:
            return f"Signal({self._value!r})"


class SessionSignal[T]:
    """Session-scoped signal (React 19-style per-client state).

    Unlike regular Signal which shares state across all users,
    SessionSignal stores its value per-session, providing isolated
    state for each WebSocket connection.

    Usage:
        # Instead of module-level shared signal:
        # _username = Signal("")  # SHARED - bug!

        # Use session signal for per-user state:
        _username = SessionSignal("", name="username")  # ISOLATED - correct!
    """

    __slots__ = ("_computeds", "_default", "_effects", "_lock", "_name", "_subscribers")

    def __init__(self, default: T, *, name: str | None = None) -> None:
        self._default = default
        self._name = name or str(uuid.uuid4())
        self._subscribers: set[Any] = set()
        self._effects: set[Any] = set()
        self._computeds: set[Any] = set()
        self._lock = threading.Lock()

    def _get_session(self) -> Any:
        """Get current session from context."""
        # Import here to avoid circular dependency
        from wtfui.web.server.app import get_current_session

        return get_current_session()

    @property
    def value(self) -> T:
        from wtfui.core.computed import get_evaluating_computed
        from wtfui.core.effect import get_running_effect

        effect = get_running_effect()
        computed = get_evaluating_computed()

        with self._lock:
            if effect is not None:
                self._effects.add(effect)
            if computed is not None:
                self._computeds.add(computed)

            # Get value from session, or use default
            session = self._get_session()
            if session is not None:
                val = session.signal_values.get(self._name, self._default)
            else:
                val = self._default

        if effect is not None:
            effect._track_signal(self)
        if computed is not None:
            computed._track_signal(self)

        return val

    @value.setter
    def value(self, new_value: T) -> None:
        subscribers_to_notify = []
        effects_to_schedule = []
        computeds_to_invalidate = []

        with self._lock:
            session = self._get_session()
            if session is None:
                # No session context - store locally (for SSR or testing)
                old_value = self._default
                self._default = new_value
            else:
                old_value = session.signal_values.get(self._name, self._default)
                session.signal_values[self._name] = new_value

            if old_value != new_value:
                subscribers_to_notify = list(self._subscribers)
                effects_to_schedule = list(self._effects)
                computeds_to_invalidate = list(self._computeds)

        for subscriber in subscribers_to_notify:
            subscriber()

        for effect in effects_to_schedule:
            effect.schedule()

        for computed in computeds_to_invalidate:
            computed.invalidate()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.add(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._subscribers.discard(callback)

    def _remove_effect(self, effect: Effect) -> None:
        with self._lock:
            self._effects.discard(effect)

    def _remove_computed(self, computed: Computed[Any]) -> None:
        with self._lock:
            self._computeds.discard(computed)

    def __repr__(self) -> str:
        with self._lock:
            session = self._get_session()
            if session is not None:
                val = session.signal_values.get(self._name, self._default)
            else:
                val = self._default
            return f"SessionSignal({val!r}, name={self._name!r})"
