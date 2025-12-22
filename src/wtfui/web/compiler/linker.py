import ast
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wtfui.web.compiler.shaker import CallGraph

if TYPE_CHECKING:
    from wtfui.web.compiler.analyzer import SplitBrainAnalyzer
    from wtfui.web.compiler.graph import DependencyGraph


def has_rpc_decorator(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in func.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "rpc":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "rpc":
            return True
    return False


@dataclass(frozen=True)
class FunctionRef:
    name: str
    module: str
    is_rpc: bool = False
    is_intrinsic: bool = False


@dataclass
class LinkResult:
    module_name: str
    rpc_calls: list[FunctionRef] = field(default_factory=list)
    local_calls: list[FunctionRef] = field(default_factory=list)
    intrinsic_calls: list[FunctionRef] = field(default_factory=list)


class Linker:
    INTRINSICS = frozenset({"print", "len", "str", "int", "range"})

    def __init__(
        self,
        graph: DependencyGraph,
        analyzer: SplitBrainAnalyzer,
    ) -> None:
        self.graph = graph
        self.analyzer = analyzer
        self._function_registry: dict[str, dict[str, FunctionRef]] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        from wtfui.web.compiler.analyzer import ModuleType

        for module_name, node in self.graph.nodes.items():
            if node.tree is None:
                continue

            module_type = self.analyzer.get_type(module_name)
            is_server_module = module_type == ModuleType.SERVER

            module_functions: dict[str, FunctionRef] = {}

            for item in ast.walk(node.tree):
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    has_rpc_decorator = self._has_rpc_decorator(item)

                    is_rpc = is_server_module or has_rpc_decorator

                    module_functions[item.name] = FunctionRef(
                        name=item.name,
                        module=module_name,
                        is_rpc=is_rpc,
                    )

            self._function_registry[module_name] = module_functions

    def _has_rpc_decorator(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return has_rpc_decorator(func)

    def link(self, module_name: str) -> LinkResult:
        result = LinkResult(module_name=module_name)

        node = self.graph.nodes.get(module_name)
        if node is None or node.tree is None:
            return result

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
        if isinstance(call.func, ast.Name):
            name = call.func.id

            if name in self.INTRINSICS:
                return FunctionRef(
                    name=name,
                    module="__builtins__",
                    is_intrinsic=True,
                )

            module_funcs = self._function_registry.get(current_module, {})
            if name in module_funcs:
                return module_funcs[name]

            node = self.graph.nodes.get(current_module)
            if node:
                for imported in node.imports:
                    imported_funcs = self._function_registry.get(imported, {})
                    if name in imported_funcs:
                        return imported_funcs[name]

            return None

        if isinstance(call.func, ast.Attribute):
            attr_name = call.func.attr

            if isinstance(call.func.value, ast.Name):
                module_alias = call.func.value.id

                node = self.graph.nodes.get(current_module)
                if node:
                    for imported in node.imports:
                        if imported.endswith(f".{module_alias}") or imported == module_alias:
                            imported_funcs = self._function_registry.get(imported, {})
                            if attr_name in imported_funcs:
                                return imported_funcs[attr_name]

            return None

        return None

    def get_rpc_functions(self, module_name: str) -> list[FunctionRef]:
        result = self.link(module_name)
        return result.rpc_calls

    def get_all_rpc_endpoints(self) -> dict[str, list[FunctionRef]]:
        endpoints: dict[str, list[FunctionRef]] = {}

        for module_name in self._function_registry:
            rpc_funcs = [ref for ref in self._function_registry[module_name].values() if ref.is_rpc]
            if rpc_funcs:
                endpoints[module_name] = rpc_funcs

        return endpoints

    def generate_rpc_stub(self, func_ref: FunctionRef) -> str:
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


def filter_unreachable(
    functions: set[str],
    graph: CallGraph,
    entry: str,
    preserve: set[str] | None = None,
) -> set[str]:
    preserve = preserve or set()
    reachable = graph.reachable_from(entry)

    if graph.has_any_dynamic_dispatch():
        dynamic_funcs = [f for f in reachable if graph.has_dynamic_dispatch(f)]
        if dynamic_funcs:
            warnings.warn(
                f"Dynamic dispatch detected in {dynamic_funcs}. "
                "Tree shaking may remove required functions.",
                stacklevel=2,
            )

    return (functions & reachable) | (functions & preserve)
