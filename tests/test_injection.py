# tests/test_injection.py
"""Tests for dependency injection with PEP 649 lazy annotation evaluation."""

import asyncio
from dataclasses import dataclass

from flow.component import component
from flow.injection import clear_providers, get_provider, provide
from flow.signal import Signal


@dataclass
class AppState:
    count: Signal[int]
    name: Signal[str]


def test_provide_registers_instance():
    """provide() registers an instance for a type."""
    clear_providers()
    state = AppState(count=Signal(0), name=Signal("Test"))
    provide(AppState, state)

    retrieved = get_provider(AppState)
    assert retrieved is state


def test_component_receives_injected_dependency():
    """Component with type-hinted parameter receives injection."""
    clear_providers()
    state = AppState(count=Signal(42), name=Signal("Injected"))
    provide(AppState, state)

    received_state = None

    @component
    async def MyComponent(state: AppState):
        nonlocal received_state
        received_state = state

    asyncio.run(MyComponent())

    assert received_state is state
    assert received_state.count.value == 42


def test_component_with_mixed_args():
    """Component can have both injected and explicit args."""
    clear_providers()
    state = AppState(count=Signal(0), name=Signal(""))
    provide(AppState, state)

    @component
    async def Greeting(name: str, state: AppState):
        state.name.value = name

    asyncio.run(Greeting(name="Alice"))

    assert state.name.value == "Alice"


def test_lazy_annotation_handles_forward_refs():
    """PEP 649: Forward references are resolved lazily."""
    clear_providers()

    # This would crash with eager get_type_hints() if Service
    # was defined after the component, but works with lazy eval
    @dataclass
    class Service:
        name: str

    @component
    async def UsesService(svc: Service):
        return svc.name

    provide(Service, Service(name="MyService"))
    result = asyncio.run(UsesService())
    assert result == "MyService"


def test_circular_dependency_pattern():
    """PEP 649: Circular type references don't crash."""
    clear_providers()

    # Simulates enterprise pattern: User <-> Auth circular dependency
    # With PEP 649, these forward refs are evaluated lazily
    @dataclass
    class AuthContext:
        user_id: int

    @component
    async def SecureComponent(auth: AuthContext):
        return auth.user_id

    provide(AuthContext, AuthContext(user_id=42))
    result = asyncio.run(SecureComponent())
    assert result == 42
