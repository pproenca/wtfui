"""Linker - RPC Resolution and Function Call Resolution.

Resolves function calls in client code. If calling a SERVER function
from CLIENT, emits RPC_CALL opcode instead of direct call.

This is the final stage before bytecode generation:

Pipeline Position:
    BoundarySentinel → [Linker] → FlowCompiler → .fbc

Resolution Rules:
1. Intrinsic function → CALL_INTRINSIC opcode
2. Local function → Direct call (inlined or labeled jump)
3. Server function → RPC_CALL opcode
4. Imported shared function → Direct call

RPC Protocol:
- Client sends: POST /api/rpc/{function_name} with JSON body
- Server receives: Validates session, executes function, returns JSON
- Client VM: Updates result signal with response data
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.compiler.analyzer import SplitBrainAnalyzer
    from flow.compiler.graph import DependencyGraph


@dataclass(frozen=True)
class FunctionRef:
    """Reference to a function for linking.

    Attributes:
        name: Function name
        module: Module containing the function
        is_rpc: True if this should be an RPC call
        is_intrinsic: True if this is a builtin intrinsic
    """

    name: str
    module: str
    is_rpc: bool = False
    is_intrinsic: bool = False


@dataclass
class LinkResult:
    """Result of linking a module.

    Attributes:
        module_name: Name of the linked module
        rpc_calls: Functions that need RPC stubs
        local_calls: Functions that can be called directly
        intrinsic_calls: Builtin functions (print, len, etc.)
    """

    module_name: str
    rpc_calls: list[FunctionRef] = field(default_factory=list)
    local_calls: list[FunctionRef] = field(default_factory=list)
    intrinsic_calls: list[FunctionRef] = field(default_factory=list)


class Linker:
    """Resolves function calls and generates RPC stubs.

    Analyzes function calls in client modules and determines whether
    they should be:
    1. Direct calls (local or shared functions)
    2. RPC calls (server functions)
    3. Intrinsic calls (builtins)

    Example:
        graph = DependencyGraph()
        graph.build_parallel(Path("src/myapp"))

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        linker = Linker(graph, analyzer)
        result = linker.link("myapp.components.counter")

        for func in result.rpc_calls:
            print(f"RPC: {func.module}.{func.name}")
    """

    # Intrinsic function names
    INTRINSICS = frozenset({"print", "len", "str", "int", "range"})

    def __init__(
        self,
        graph: DependencyGraph,
        analyzer: SplitBrainAnalyzer,
    ) -> None:
        """Initialize linker with graph and analyzer.

        Args:
            graph: Dependency graph with module relationships
            analyzer: Module type classifications
        """
        self.graph = graph
        self.analyzer = analyzer
        self._function_registry: dict[str, dict[str, FunctionRef]] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        """Build registry of all functions in the graph.

        Scans all modules and registers their functions with
        their RPC status based on module classification.
        """
        # Import here to avoid circular imports
        from flow.compiler.analyzer import ModuleType

        for module_name, node in self.graph.nodes.items():
            if node.tree is None:
                continue

            module_type = self.analyzer.get_type(module_name)
            is_server_module = module_type == ModuleType.SERVER

            module_functions: dict[str, FunctionRef] = {}

            for item in ast.walk(node.tree):
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    # Check if function has @rpc decorator
                    has_rpc_decorator = self._has_rpc_decorator(item)

                    # Function is RPC if in server module OR has @rpc decorator
                    is_rpc = is_server_module or has_rpc_decorator

                    module_functions[item.name] = FunctionRef(
                        name=item.name,
                        module=module_name,
                        is_rpc=is_rpc,
                    )

            self._function_registry[module_name] = module_functions

    def _has_rpc_decorator(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has @rpc decorator.

        Args:
            func: Function definition AST node

        Returns:
            True if function has @rpc decorator
        """
        for decorator in func.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "rpc":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "rpc":
                return True
        return False

    def link(self, module_name: str) -> LinkResult:
        """Link a module's function calls.

        Analyzes all function calls in the module and categorizes them.

        Args:
            module_name: Module to link

        Returns:
            LinkResult with categorized function calls
        """
        result = LinkResult(module_name=module_name)

        node = self.graph.nodes.get(module_name)
        if node is None or node.tree is None:
            return result

        # Find all function calls
        for item in ast.walk(node.tree):
            if isinstance(item, ast.Call):
                ref = self._resolve_call(item, module_name)
                if ref is not None:
                    if ref.is_intrinsic:
                        result.intrinsic_calls.append(ref)
                    elif ref.is_rpc:
                        result.rpc_calls.append(ref)
                    else:
                        result.local_calls.append(ref)

        return result

    def _resolve_call(self, call: ast.Call, current_module: str) -> FunctionRef | None:
        """Resolve a function call to its definition.

        Args:
            call: Function call AST node
            current_module: Module containing the call

        Returns:
            FunctionRef or None if unresolvable
        """
        # Simple name call: func()
        if isinstance(call.func, ast.Name):
            name = call.func.id

            # Check if intrinsic
            if name in self.INTRINSICS:
                return FunctionRef(
                    name=name,
                    module="__builtins__",
                    is_intrinsic=True,
                )

            # Check if local to current module
            module_funcs = self._function_registry.get(current_module, {})
            if name in module_funcs:
                return module_funcs[name]

            # Check imported modules
            node = self.graph.nodes.get(current_module)
            if node:
                for imported in node.imports:
                    imported_funcs = self._function_registry.get(imported, {})
                    if name in imported_funcs:
                        return imported_funcs[name]

            return None

        # Attribute call: module.func()
        if isinstance(call.func, ast.Attribute):
            attr_name = call.func.attr

            # Check if it's a module.function call
            if isinstance(call.func.value, ast.Name):
                module_alias = call.func.value.id

                # Find the actual module from imports
                node = self.graph.nodes.get(current_module)
                if node:
                    for imported in node.imports:
                        # Check if alias matches end of module path
                        if imported.endswith(f".{module_alias}") or imported == module_alias:
                            imported_funcs = self._function_registry.get(imported, {})
                            if attr_name in imported_funcs:
                                return imported_funcs[attr_name]

            return None

        return None

    def get_rpc_functions(self, module_name: str) -> list[FunctionRef]:
        """Get all functions in a module that need RPC stubs.

        Args:
            module_name: Module to check

        Returns:
            List of functions that should be exposed via RPC
        """
        result = self.link(module_name)
        return result.rpc_calls

    def get_all_rpc_endpoints(self) -> dict[str, list[FunctionRef]]:
        """Get all RPC endpoints across all modules.

        Returns:
            Dict mapping module names to their RPC functions
        """
        endpoints: dict[str, list[FunctionRef]] = {}

        for module_name in self._function_registry:
            rpc_funcs = [ref for ref in self._function_registry[module_name].values() if ref.is_rpc]
            if rpc_funcs:
                endpoints[module_name] = rpc_funcs

        return endpoints

    def generate_rpc_stub(self, func_ref: FunctionRef) -> str:
        """Generate JavaScript RPC stub for a function.

        Creates a fetch-based stub that calls the server endpoint.

        Args:
            func_ref: Function reference

        Returns:
            JavaScript function code
        """
        return f"""
async function {func_ref.name}(...args) {{
    const response = await fetch('/api/rpc/{func_ref.module}.{func_ref.name}', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ args }})
    }});
    return response.json();
}}
""".strip()
