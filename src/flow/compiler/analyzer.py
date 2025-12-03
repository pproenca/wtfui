"""SplitBrainAnalyzer - Client/Server Module Classification.

Analyzes Python modules to determine whether they contain client-side
(UI) logic or server-side (backend) logic. This classification enables
the security firewall (BoundarySentinel) and automatic RPC generation.

Classification Rules:
- CLIENT: UI components, reactive primitives, DOM manipulation
- SERVER: Database access, file system, network, os module, subprocess

Pipeline Position:
    DependencyGraph → [SplitBrainAnalyzer] → BoundarySentinel → Linker

Security Model:
- Client code can ONLY call server code via RPC
- Client code CANNOT import server modules directly
- Server code can import other server modules freely
"""

from __future__ import annotations

import ast
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.compiler.graph import DependencyGraph


class ModuleType(Enum):
    """Classification of module types.

    CLIENT: Contains UI logic, can run in browser
    SERVER: Contains backend logic, must stay on server
    SHARED: Pure utility code, safe for both environments
    """

    CLIENT = auto()
    SERVER = auto()
    SHARED = auto()


# Imports that indicate server-side code
SERVER_INDICATORS: frozenset[str] = frozenset(
    {
        # Standard library - OS/System
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "tempfile",
        # Standard library - File I/O
        "io",
        "open",
        # Standard library - Network
        "socket",
        "ssl",
        "http.server",
        "urllib",
        "ftplib",
        "smtplib",
        # Standard library - Processes
        "multiprocessing",
        "threading",
        "signal",
        "ctypes",
        # Databases
        "sqlite3",
        "psycopg2",
        "pymysql",
        "pymongo",
        "redis",
        "sqlalchemy",
        "prisma",
        "databases",
        # Web frameworks (server-side)
        "flask",
        "django",
        "fastapi",
        "starlette",
        "uvicorn",
        "gunicorn",
        # Environment/Secrets
        "dotenv",
        "boto3",
        "botocore",
    }
)

# Imports that indicate client-side code
CLIENT_INDICATORS: frozenset[str] = frozenset(
    {
        # Flow UI primitives
        "flow.ui",
        "flow.element",
        "flow.signal",
        "flow.effect",
        "flow.computed",
        "flow.component",
        "flow.style",
        # Flow UI elements
        "Div",
        "Button",
        "Text",
        "Input",
        "VStack",
        "HStack",
        "Grid",
        # Signal primitives
        "Signal",
        "Effect",
        "Computed",
    }
)


class SplitBrainAnalyzer:
    """Analyzes modules to classify as CLIENT or SERVER.

    Uses AST inspection to determine module type based on:
    1. Import statements (which packages are used)
    2. Function decorators (@rpc indicates server function)
    3. Usage of UI primitives (Signal, Div, etc.)

    Example:
        from flow.compiler.graph import DependencyGraph

        graph = DependencyGraph()
        graph.build_parallel(Path("src/myapp"))

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        # Check module type
        if analyzer.get_type("myapp.api") == ModuleType.SERVER:
            # Handle server module
            pass
    """

    def __init__(self, graph: DependencyGraph) -> None:
        """Initialize analyzer with dependency graph.

        Args:
            graph: Pre-built dependency graph
        """
        self.graph = graph
        self.classifications: dict[str, ModuleType] = {}

    def analyze(self) -> None:
        """Analyze all modules in the graph.

        Classifies each module as CLIENT, SERVER, or SHARED.
        """
        for module_name, node in self.graph.nodes.items():
            if node.tree is not None:
                self.classifications[module_name] = self._classify_module(node.tree, node.imports)
            else:
                # No AST available, assume SHARED
                self.classifications[module_name] = ModuleType.SHARED

    def _classify_module(self, tree: ast.Module, imports: set[str]) -> ModuleType:
        """Classify a single module based on its AST and imports.

        Priority:
        1. If has @rpc decorators → SERVER
        2. If imports SERVER_INDICATORS → SERVER
        3. If imports CLIENT_INDICATORS → CLIENT
        4. Otherwise → SHARED

        Args:
            tree: Parsed AST
            imports: Set of imported module names

        Returns:
            ModuleType classification
        """
        # Check for server indicators
        has_server = any(self._matches_indicator(imp, SERVER_INDICATORS) for imp in imports)

        # Check for client indicators
        has_client = any(self._matches_indicator(imp, CLIENT_INDICATORS) for imp in imports)

        # Check for @rpc decorator (indicates server function)
        has_rpc = self._has_rpc_decorator(tree)

        # Check for UI element usage
        has_ui_elements = self._has_ui_elements(tree)

        # Classification logic
        if has_rpc or has_server:
            return ModuleType.SERVER
        elif has_client or has_ui_elements:
            return ModuleType.CLIENT
        else:
            return ModuleType.SHARED

    def _matches_indicator(self, import_name: str, indicators: frozenset[str]) -> bool:
        """Check if import matches any indicator.

        Handles both exact matches and prefix matches for nested modules.

        Args:
            import_name: Imported module name
            indicators: Set of indicator patterns

        Returns:
            True if import matches any indicator
        """
        if import_name in indicators:
            return True

        # Check if it's a submodule of an indicator
        for indicator in indicators:
            if import_name.startswith(f"{indicator}."):
                return True
            if indicator.startswith(f"{import_name}."):
                return True

        return False

    def _has_rpc_decorator(self, tree: ast.Module) -> bool:
        """Check if module has any @rpc decorated functions.

        Args:
            tree: Parsed AST

        Returns:
            True if any function has @rpc decorator
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "rpc":
                        return True
                    if isinstance(decorator, ast.Attribute) and decorator.attr == "rpc":
                        return True
        return False

    def _has_ui_elements(self, tree: ast.Module) -> bool:
        """Check if module uses UI elements (Div, Button, etc.).

        Args:
            tree: Parsed AST

        Returns:
            True if any UI element is used
        """
        ui_elements = {"Div", "Button", "Text", "Input", "VStack", "HStack", "Grid"}

        for node in ast.walk(tree):
            # Check for with Div(): pattern
            if isinstance(node, ast.With):
                for item in node.items:
                    if (
                        isinstance(item.context_expr, ast.Call)
                        and isinstance(item.context_expr.func, ast.Name)
                        and item.context_expr.func.id in ui_elements
                    ):
                        return True

            # Check for Element() calls or Signal() usage
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and (node.func.id in ui_elements or node.func.id == "Signal")
            ):
                return True

        return False

    def get_type(self, module_name: str) -> ModuleType:
        """Get the classification for a module.

        Args:
            module_name: Dotted module name

        Returns:
            ModuleType (defaults to SHARED if not found)
        """
        return self.classifications.get(module_name, ModuleType.SHARED)

    def get_client_modules(self) -> list[str]:
        """Get all client-side modules.

        Returns:
            List of module names classified as CLIENT
        """
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.CLIENT]

    def get_server_modules(self) -> list[str]:
        """Get all server-side modules.

        Returns:
            List of module names classified as SERVER
        """
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.SERVER]

    def get_shared_modules(self) -> list[str]:
        """Get all shared modules.

        Returns:
            List of module names classified as SHARED
        """
        return [name for name, mtype in self.classifications.items() if mtype == ModuleType.SHARED]
