# src/flow/__init__.py
"""Flow - A Pythonic UI Framework using context managers and signals.

A Python UI framework based on these core principles:

1. **Indentation is Topology** - `with` blocks define DOM hierarchy
2. **Reactivity via Signals** - Fine-grained, thread-safe updates without setState
3. **Dependency Injection** - Lazy type hints for context injection (PEP 649)
4. **Async by Default** - Rendering is non-blocking
5. **Universal Runtime** - Same code runs on server and client (Wasm) via Renderer Protocol
6. **Zero-Build Dev** - No compilation step; import hooks handle transpilation

Requires Python 3.14+ for No-GIL (PEP 703) and PEP 649 (deferred annotations).
"""

from flow.component import component
from flow.computed import Computed
from flow.effect import Effect
from flow.element import Element
from flow.signal import Signal

__all__ = [
    "Computed",
    "Effect",
    "Element",
    "Signal",
    "component",
]

__version__ = "0.1.0"
