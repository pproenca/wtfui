import ast
import warnings
from typing import TYPE_CHECKING

from wtfui.web.compiler.linker import has_rpc_decorator

if TYPE_CHECKING:
    from types import CodeType


SERVER_ONLY_MODULES: set[str] = {
    "sqlalchemy",
    "psycopg2",
    "pymongo",
    "redis",
    "sqlite3",
    "boto3",
    "botocore",
    "google.cloud",
    "azure",
    "pandas",
    "numpy",
    "os",
    "subprocess",
    "shutil",
    "pathlib",
    "celery",
    "dramatiq",
    "rq",
    "dotenv",
    "hvac",
    "keyring",
}


class BundleOptimizer(ast.NodeTransformer):
    """AST transformer that optimizes client bundle by removing server-only code.

    WARNING: This is NOT a security boundary. It is purely a bundle size
    optimization. Server-side secrets must never be in client-reachable code.
    """

    def __init__(self) -> None:
        super().__init__()
        self.warnings: list[str] = []

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        remaining = []
        for alias in node.names:
            module_root = alias.name.split(".")[0]
            if module_root in SERVER_ONLY_MODULES:
                self.warnings.append(f"Removed server-only import: {alias.name}")
            else:
                remaining.append(alias)

        if not remaining:
            return None

        node.names = remaining
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom | None:
        if node.module:
            module_root = node.module.split(".")[0]
            if module_root in SERVER_ONLY_MODULES:
                self.warnings.append(f"Removed server-only import: from {node.module}")
                return None
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        if self._has_rpc_decorator(node):
            node.body = self._create_fetch_stub(node.name, _is_async=True)
        else:
            self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if self._has_rpc_decorator(node):
            node.body = self._create_fetch_stub(node.name, _is_async=False)
        else:
            self.generic_visit(node)
        return node

    def _has_rpc_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return has_rpc_decorator(node)

    def _create_fetch_stub(self, _func_name: str, _is_async: bool) -> list[ast.stmt]:
        return [ast.Pass()]


def transform_for_client(source: str) -> str:
    tree = ast.parse(source)
    transformer = BundleOptimizer()
    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    for warning in transformer.warnings:
        warnings.warn(warning, stacklevel=2)

    return ast.unparse(transformed)


def compile_for_client(source: str, filename: str = "<fuse>") -> CodeType:
    tree = ast.parse(source)
    transformer = BundleOptimizer()
    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    return compile(transformed, filename, "exec")
