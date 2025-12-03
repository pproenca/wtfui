"""Dependency Graph Builder for FlowByte Compilation.

Builds a module dependency graph using parallel parsing (No-GIL optimized).
This is the first stage of the compilation pipeline:

    app.py → AST → DependencyGraph → SplitBrainAnalyzer → ...

Key Design (Steering Council Adjustment #2):
- Workers ONLY read files and parse ASTs (no shared state writes)
- Main thread aggregates results sequentially
- No lock contention, no cache-line bouncing

Threading Model (No-GIL Python 3.14):
- Each worker thread returns (module_name, imports, ast) tuple
- Main thread updates self.nodes and self.asts atomically
- ~99% time in parsing (embarrassingly parallel), <1% in aggregation
"""

from __future__ import annotations

import ast
import concurrent.futures
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Set
    from pathlib import Path


class DependencyNode:
    """Represents a module in the dependency graph.

    Attributes:
        name: Module name (e.g., "app.components.counter")
        path: Absolute path to the Python file
        imports: Set of imported module names
        tree: Parsed AST (or None if parsing failed)
    """

    __slots__ = ("imports", "name", "path", "tree")

    def __init__(
        self,
        name: str,
        path: Path,
        imports: set[str],
        tree: ast.Module | None,
    ) -> None:
        self.name = name
        self.path = path
        self.imports = imports
        self.tree = tree


class DependencyGraph:
    """Lock-free parallel dependency graph builder.

    Builds a graph of module dependencies by parsing Python files in parallel.
    Uses the sharded collection pattern to avoid lock contention:
    - Worker threads return results as tuples
    - Main thread aggregates results sequentially

    Example:
        graph = DependencyGraph()
        graph.build_parallel(Path("src/myapp"))

        # Get all imports for a module
        module_imports = graph.get_imports("myapp.components")

        # Get topological order for compilation
        order = graph.topological_order()
    """

    def __init__(self) -> None:
        """Initialize empty dependency graph."""
        self.nodes: dict[str, DependencyNode] = {}

    def build_parallel(self, root: Path, max_workers: int | None = None) -> None:
        """Build graph using ThreadPoolExecutor (No-GIL).

        CRITICAL: Avoid shared-state writes during parallel phase.
        Each worker returns (module_name, path, imports, ast) tuple.
        Main thread aggregates results sequentially.

        Args:
            root: Root directory to scan for Python files
            max_workers: Maximum worker threads (None = cpu_count)
        """
        py_files = list(root.rglob("*.py"))

        if not py_files:
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all parse jobs
            futures = {executor.submit(self._parse_file, f, root): f for f in py_files}

            # Collect results as they complete (NO SHARED WRITES IN WORKERS)
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        module_name, imports, tree = result

                        # MAIN THREAD ONLY: Update shared data structures
                        self.nodes[module_name] = DependencyNode(
                            name=module_name,
                            path=file_path,
                            imports=imports,
                            tree=tree,
                        )

                except Exception as e:
                    # Log parsing errors but continue with other files
                    print(f"Error parsing {file_path}: {e}")

    def _parse_file(self, path: Path, root: Path) -> tuple[str, set[str], ast.Module] | None:
        """Parse single file (thread-safe, NO SHARED STATE ACCESS).

        Returns tuple for main thread to aggregate.

        Args:
            path: Path to Python file
            root: Root directory for relative module names

        Returns:
            Tuple of (module_name, imports, ast) or None on error
        """
        try:
            source = path.read_text()
            tree = ast.parse(source)

            # Convert path to module name
            try:
                rel_path = path.relative_to(root)
            except ValueError:
                # path not under root, use absolute
                rel_path = path

            # Remove .py extension and convert to dotted module name
            parts = list(rel_path.parts)
            if parts and parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]  # Remove .py
            module_name = ".".join(parts)

            # Extract imports
            imports = self._extract_imports(tree)

            return module_name, imports, tree

        except SyntaxError:
            # Skip files with syntax errors
            return None
        except OSError:
            # Skip files that can't be read
            return None

    def _extract_imports(self, tree: ast.Module) -> set[str]:
        """Extract import statements from AST.

        Args:
            tree: Parsed Python AST

        Returns:
            Set of imported module names
        """
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        return imports

    def get_imports(self, module_name: str) -> Set[str]:
        """Get imports for a specific module.

        Args:
            module_name: Dotted module name

        Returns:
            Set of imported module names (empty if module not found)
        """
        node = self.nodes.get(module_name)
        return node.imports if node else set()

    def get_ast(self, module_name: str) -> ast.Module | None:
        """Get parsed AST for a module.

        Args:
            module_name: Dotted module name

        Returns:
            Parsed AST or None if module not found
        """
        node = self.nodes.get(module_name)
        return node.tree if node else None

    def get_dependents(self, module_name: str) -> set[str]:
        """Get modules that depend on the given module.

        Args:
            module_name: Dotted module name to find dependents of

        Returns:
            Set of module names that import this module
        """
        dependents: set[str] = set()
        for name, node in self.nodes.items():
            if module_name in node.imports:
                dependents.add(name)
        return dependents

    def topological_order(self) -> list[str]:
        """Return modules in topological order (dependencies first).

        Uses Kahn's algorithm for topological sort.
        Modules with no dependencies are output first.

        Returns:
            List of module names in dependency order

        Raises:
            ValueError: If circular dependency detected
        """
        # Calculate in-degree: count how many internal modules each module imports
        in_degree: dict[str, int] = {}

        for name, node in self.nodes.items():
            # Count internal dependencies (imports that are in our graph)
            internal_imports = sum(1 for imp in node.imports if imp in self.nodes)
            in_degree[name] = internal_imports

        # Start with modules that have no internal dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # For each module that imports the current module, reduce its in-degree
            for name, node in self.nodes.items():
                if current in node.imports:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(result) != len(self.nodes):
            # Circular dependency detected
            remaining = set(self.nodes.keys()) - set(result)
            raise ValueError(f"Circular dependency detected in: {remaining}")

        return result

    def __len__(self) -> int:
        """Return number of modules in the graph."""
        return len(self.nodes)

    def __contains__(self, module_name: str) -> bool:
        """Check if module is in the graph."""
        return module_name in self.nodes
