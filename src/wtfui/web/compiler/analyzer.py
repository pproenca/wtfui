"""Bundle analyzer for determining client/server module classification.

This module provides analysis tools for bundle optimization, classifying
modules as client, server, or shared based on their imports and usage.
"""

import ast
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.web.compiler.graph import DependencyGraph


class ModuleType(Enum):
    CLIENT = auto()
    SERVER = auto()
    SHARED = auto()


SERVER_INDICATORS: frozenset[str] = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "tempfile",
        "io",
        "open",
        "socket",
        "ssl",
        "http.server",
        "urllib",
        "ftplib",
        "smtplib",
        "multiprocessing",
        "threading",
        "signal",
        "ctypes",
        "sqlite3",
        "psycopg2",
        "pymysql",
        "pymongo",
        "redis",
        "sqlalchemy",
        "prisma",
        "databases",
        "flask",
        "django",
        "fastapi",
        "starlette",
        "uvicorn",
        "gunicorn",
        "dotenv",
        "boto3",
        "botocore",
    }
)


CLIENT_INDICATORS: frozenset[str] = frozenset(
    {
        "wtfui.ui",
        "wtfui.element",
        "wtfui.signal",
        "wtfui.effect",
        "wtfui.computed",
        "wtfui.component",
        "wtfui.style",
        "wtfui.core",
        "wtfui.core.element",
        "wtfui.core.signal",
        "wtfui.core.effect",
        "wtfui.core.computed",
        "wtfui.core.component",
        "wtfui.core.context",
        "Div",
        "Button",
        "Text",
        "Input",
        "VStack",
        "HStack",
        "Grid",
        "Signal",
        "Effect",
        "Computed",
    }
)


class SplitBrainAnalyzer:
    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph
        self.classifications: dict[str, ModuleType] = {}

    def analyze(self) -> None:
        for module_name, node in self.graph.nodes.items():
            if node.tree is not None:
                self.classifications[module_name] = self._classify_module(node.tree, node.imports)
            else:
                self.classifications[module_name] = ModuleType.SHARED

    def _classify_module(self, tree: ast.Module, imports: set[str]) -> ModuleType:
        has_server = any(self._matches_indicator(imp, SERVER_INDICATORS) for imp in imports)

        has_client = any(self._matches_indicator(imp, CLIENT_INDICATORS) for imp in imports)

        has_rpc = self._has_rpc_decorator(tree)

        has_ui_elements = self._has_ui_elements(tree)

        if has_rpc or has_server:
            return ModuleType.SERVER
        elif has_client or has_ui_elements:
            return ModuleType.CLIENT
        else:
            return ModuleType.SHARED

    def _matches_indicator(self, import_name: str, indicators: frozenset[str]) -> bool:
        if import_name in indicators:
            return True

        for indicator in indicators:
            if import_name.startswith(f"{indicator}."):
                return True
            if indicator.startswith(f"{import_name}."):
                return True

        return False

    def _has_rpc_decorator(self, tree: ast.Module) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "rpc":
                        return True
                    if isinstance(decorator, ast.Attribute) and decorator.attr == "rpc":
                        return True
        return False

    def _has_ui_elements(self, tree: ast.Module) -> bool:
        ui_elements = {"Div", "Button", "Text", "Input", "VStack", "HStack", "Grid"}

        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    if (
                        isinstance(item.context_expr, ast.Call)
                        and isinstance(item.context_expr.func, ast.Name)
                        and item.context_expr.func.id in ui_elements
                    ):
                        return True

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and (node.func.id in ui_elements or node.func.id == "Signal")
            ):
                return True

        return False

    def get_type(self, module_name: str) -> ModuleType:
        return self.classifications.get(module_name, ModuleType.SHARED)

    def get_client_modules(self) -> list[str]:
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.CLIENT]

    def get_server_modules(self) -> list[str]:
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.SERVER]

    def get_shared_modules(self) -> list[str]:
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.SHARED]
