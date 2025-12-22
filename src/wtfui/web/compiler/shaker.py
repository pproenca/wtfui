import ast
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import ClassVar


class CallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)

        self.generic_visit(node)


class DynamicDispatchVisitor(ast.NodeVisitor):
    DYNAMIC_PATTERNS: ClassVar[set[str]] = {"getattr", "globals", "locals", "eval", "exec"}

    def __init__(self) -> None:
        self.has_dynamic = False

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in self.DYNAMIC_PATTERNS:
            self.has_dynamic = True

        if (
            isinstance(node.func, ast.Subscript)
            and isinstance(node.func.value, ast.Call)
            and isinstance(node.func.value.func, ast.Name)
            and node.func.value.func.id in self.DYNAMIC_PATTERNS
        ):
            self.has_dynamic = True
        self.generic_visit(node)


@dataclass
class CallGraph:
    _edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _all_functions: set[str] = field(default_factory=set)
    _dynamic_functions: set[str] = field(default_factory=set)

    def add_edge(self, caller: str, callee: str) -> None:
        self._edges[caller].add(callee)

    def calls_from(self, func_name: str) -> set[str]:
        return self._edges.get(func_name, set())

    def reachable_from(self, entry: str) -> set[str]:
        visited: set[str] = set()
        queue: deque[str] = deque([entry])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for callee in self._edges.get(current, set()):
                if callee not in visited and callee in self._all_functions:
                    queue.append(callee)

        return visited

    def has_dynamic_dispatch(self, func_name: str) -> bool:
        return func_name in self._dynamic_functions

    def has_any_dynamic_dispatch(self) -> bool:
        return len(self._dynamic_functions) > 0

    @classmethod
    def from_source(cls, source: str) -> CallGraph:
        tree = ast.parse(source)
        graph = cls()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                graph._all_functions.add(node.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                call_visitor = CallVisitor()
                for stmt in node.body:
                    call_visitor.visit(stmt)
                for callee in call_visitor.calls:
                    graph.add_edge(node.name, callee)

                dyn_visitor = DynamicDispatchVisitor()
                for stmt in node.body:
                    dyn_visitor.visit(stmt)
                if dyn_visitor.has_dynamic:
                    graph._dynamic_functions.add(node.name)

        return graph
