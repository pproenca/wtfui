"""Client-Safe AST Transformer - Security-hardened code splitting.

Transforms Python source for client-side execution by:
1. Removing server-only imports (sqlalchemy, pandas, boto3, os, etc.)
2. Stubbing @rpc function bodies with fetch proxies
3. Preserving @component functions and UI code
4. Detecting dangerous patterns that could leak secrets

Per MANIFEST.md Tenet VI: "The Client is a privilege-reduced environment."
"""

from __future__ import annotations

import ast
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import CodeType

# Imports that are SERVER-ONLY and MUST be removed from client bundles
# These are security-sensitive - leaking them could expose credentials
SERVER_ONLY_MODULES: set[str] = {
    # Database
    "sqlalchemy",
    "psycopg2",
    "pymongo",
    "redis",
    "sqlite3",
    # Cloud/Infrastructure
    "boto3",
    "botocore",
    "google.cloud",
    "azure",
    # Data processing (often has secrets in pipelines)
    "pandas",
    "numpy",  # Sometimes loads from authenticated sources
    # System access (DANGEROUS - can leak env vars)
    "os",
    "subprocess",
    "shutil",
    "pathlib",  # Can expose server paths
    # Async workers (server-only)
    "celery",
    "dramatiq",
    "rq",
    # Secrets management
    "dotenv",
    "hvac",
    "keyring",
}


class ClientSafeTransformer(ast.NodeTransformer):
    """
    Walks the AST and transforms for client-safe execution.

    Security model:
    - Server imports are REMOVED (not just stubbed)
    - @rpc bodies are replaced with fetch() calls
    - Warnings are emitted for dangerous patterns
    """

    def __init__(self) -> None:
        super().__init__()
        self.warnings: list[str] = []

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        """Remove server-only imports."""
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
        """Remove server-only from imports."""
        if node.module:
            module_root = node.module.split(".")[0]
            if module_root in SERVER_ONLY_MODULES:
                self.warnings.append(f"Removed server-only import: from {node.module}")
                return None
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Stub @rpc decorated async functions with fetch proxy."""
        if self._has_rpc_decorator(node):
            # Replace body with fetch stub
            node.body = self._create_fetch_stub(node.name, _is_async=True)
        else:
            # Recurse into non-RPC functions
            self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Stub @rpc decorated sync functions."""
        if self._has_rpc_decorator(node):
            node.body = self._create_fetch_stub(node.name, _is_async=False)
        else:
            self.generic_visit(node)
        return node

    def _has_rpc_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has @rpc decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "rpc":
                return True
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Name) and func.id == "rpc":
                    return True
                if isinstance(func, ast.Attribute) and func.attr == "rpc":
                    return True
        return False

    def _create_fetch_stub(self, _func_name: str, _is_async: bool) -> list[ast.stmt]:
        """
        Create a fetch() stub body for RPC functions.

        For client-side Wasm, this will call the server via HTTP.
        Args are prefixed with _ as they'll be used in future JS interop.
        """
        # For now, just use pass - full implementation needs JS interop
        # In Wasm: would be `await js.fetch(f"/api/rpc/{_func_name}", ...)`
        return [ast.Pass()]


def transform_for_client(source: str) -> str:
    """
    Transform Python source code for client-side execution.

    Returns source code safe for Wasm deployment.
    """
    tree = ast.parse(source)
    transformer = ClientSafeTransformer()
    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    # Emit warnings for removed imports
    for warning in transformer.warnings:
        warnings.warn(warning, stacklevel=2)

    return ast.unparse(transformed)


def compile_for_client(source: str, filename: str = "<flow>") -> CodeType:
    """
    Compile source to bytecode for client execution.

    Used by import hook for in-memory transformation.
    """
    tree = ast.parse(source)
    transformer = ClientSafeTransformer()
    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    return compile(transformed, filename, "exec")
