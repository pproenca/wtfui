import ast
import logging
import threading

logger = logging.getLogger(__name__)


class ComponentRegistry:
    def __init__(self) -> None:
        self._components: dict[str, ast.AsyncFunctionDef | ast.FunctionDef] = {}
        self._lock = threading.Lock()

    def scan(self, tree: ast.AST) -> None:
        components_to_add = []
        for node in ast.walk(tree):
            if isinstance(
                node, ast.AsyncFunctionDef | ast.FunctionDef
            ) and self._has_component_decorator(node):
                if self._has_parameters(node):
                    logger.warning(
                        f"Component '{node.name}' has parameters but component "
                        "parameter binding is not yet supported. Arguments will "
                        "be silently ignored. Component skipped from registration."
                    )
                    continue
                components_to_add.append((node.name, node))

        with self._lock:
            for name, node in components_to_add:
                self._components[name] = node

    def _has_component_decorator(self, node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
        for decorator in node.decorator_list:
            match decorator:
                case ast.Name(id="component"):
                    return True
                case ast.Attribute(attr="component"):
                    return True
        return False

    def _has_parameters(self, node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
        args = node.args

        positional_args = [arg for arg in args.args if arg.arg != "self"]

        return (
            len(positional_args) > 0
            or len(args.posonlyargs) > 0
            or args.vararg is not None
            or len(args.kwonlyargs) > 0
            or args.kwarg is not None
        )

    def __contains__(self, name: str) -> bool:
        return name in self._components

    def get(self, name: str) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
        return self._components.get(name)

    def get_body(self, name: str) -> list[ast.stmt] | None:
        node = self._components.get(name)
        return node.body if node else None
