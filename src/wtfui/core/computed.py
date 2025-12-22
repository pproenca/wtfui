import threading
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from wtfui.core.effect import Effect


_evaluating_computed: ContextVar[Computed[Any] | None] = ContextVar(
    "evaluating_computed", default=None
)


_evaluation_stack: ContextVar[set[int] | None] = ContextVar("evaluation_stack", default=None)


def get_evaluating_computed() -> Computed[Any] | None:
    return _evaluating_computed.get()


class Computed[T]:
    __slots__ = (
        "__weakref__",
        "_computed_event",
        "_computeds",
        "_computing",
        "_effects",
        "_is_dirty",
        "_lock",
        "_tracked_computeds",
        "_tracked_signals",
        "_value",
        "fn",
    )

    def __init__(self, fn: Callable[[], T]) -> None:
        self.fn = fn
        self._value = None
        self._is_dirty = True
        self._computing = False
        self._lock = threading.Lock()
        self._computed_event = threading.Event()

        self._tracked_signals = set()
        self._tracked_computeds = set()

        self._effects = set()
        self._computeds = set()

    def __call__(self) -> T:
        stack = _evaluation_stack.get()
        if stack is None:
            stack = set()
        if id(self) in stack:
            fn_name = getattr(self.fn, "__name__", "<anonymous>")
            raise RecursionError(f"Circular dependency detected in Computed({fn_name})")

        from wtfui.core.effect import get_running_effect

        running_effect = get_running_effect()
        running_computed = get_evaluating_computed()

        if running_effect is not None or running_computed is not None:
            with self._lock:
                if running_effect is not None:
                    self._effects.add(running_effect)
                if running_computed is not None:
                    self._computeds.add(running_computed)

            if running_computed is not None:
                running_computed._track_computed(self)

        if not self._is_dirty and not self._computing:
            return self._value

        with self._lock:
            if not self._is_dirty and not self._computing:
                return self._value

            if self._computing:
                should_compute = False
            elif self._is_dirty:
                self._computing = True
                self._computed_event.clear()
                should_compute = True
            else:
                should_compute = False

        if not should_compute:
            self._computed_event.wait()
            return self._value

        new_stack = stack | {id(self)}
        stack_token = _evaluation_stack.set(new_stack)
        token = _evaluating_computed.set(self)
        try:
            new_value = self.fn()
        except Exception:
            with self._lock:
                self._computing = False
                self._is_dirty = True
            self._computed_event.set()
            raise
        finally:
            _evaluating_computed.reset(token)
            _evaluation_stack.reset(stack_token)

        with self._lock:
            self._value = new_value
            self._is_dirty = False
            self._computing = False

        self._computed_event.set()
        return new_value

    def invalidate(self) -> None:
        effects_to_schedule = []
        computeds_to_invalidate = []

        with self._lock:
            if self._is_dirty:
                return
            self._is_dirty = True
            effects_to_schedule = list(self._effects)
            computeds_to_invalidate = list(self._computeds)

        for effect in effects_to_schedule:
            effect.schedule()

        for computed in computeds_to_invalidate:
            computed.invalidate()

    def _track_signal(self, signal: Any) -> None:
        with self._lock:
            self._tracked_signals.add(signal)

    def _track_computed(self, computed: Computed[Any]) -> None:
        with self._lock:
            self._tracked_computeds.add(computed)

    def _remove_effect(self, effect: Effect) -> None:
        with self._lock:
            self._effects.discard(effect)

    def _remove_computed(self, computed: Computed[Any]) -> None:
        with self._lock:
            self._computeds.discard(computed)

    def dispose(self) -> None:
        from wtfui.core.signal import Signal

        for sig in list(self._tracked_signals):
            if isinstance(sig, Signal):
                sig._remove_computed(self)
        self._tracked_signals.clear()

        for comp in list(self._tracked_computeds):
            comp._remove_computed(self)
        self._tracked_computeds.clear()

    def __repr__(self) -> str:
        fn_name = getattr(self.fn, "__name__", "<anonymous>")
        return f"Computed({fn_name}, dirty={self._is_dirty})"
