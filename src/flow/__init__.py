# src/flow/__init__.py
"""Flow - A Pythonic UI Framework using context managers and signals.

Core Features:
- Indentation is Topology: `with Div():` defines DOM hierarchy
- Atomic Reactivity: Signal → Effect → Computed
- Universal Runtime: Same code on server and client
- Zero-Build Dev: Just run `python app.py`
- FlowByte: Compile to binary bytecode for fast browser execution

Quick Start:
    from flow import component, Signal
    from flow.ui import Div, Text, Button

    count = Signal(0)

    @component
    async def App():
        with Div() as root:
            with Text(f"Count: {count.value}"):
                pass
            with Button("Inc", on_click=lambda: setattr(count, 'value', count.value + 1)):
                pass
        return root

FlowByte Compilation:
    from flow.compiler import compile_to_flowbyte, compile_parallel

    # Single-threaded compilation
    binary = compile_to_flowbyte(source_code)

    # Parallel compilation (Python 3.14 No-GIL)
    binary = compile_parallel(source_code, max_workers=4)
"""

from flow.component import component
from flow.computed import Computed
from flow.effect import Effect
from flow.element import Element
from flow.injection import get_provider, provide
from flow.rpc import rpc
from flow.signal import Signal

__all__ = [
    "Computed",
    "Effect",
    "Element",
    "Signal",
    "component",
    "get_provider",
    "provide",
    "rpc",
]

__version__ = "0.1.0"
