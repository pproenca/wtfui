import ast
import concurrent.futures
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Set
    from pathlib import Path


class DependencyNode:
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
    def __init__(self) -> None:
        self.nodes: dict[str, DependencyNode] = {}

    def build_parallel(self, root: Path, max_workers: int | None = None) -> None:
        py_files = list(root.rglob("*.py"))

        if not py_files:
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._parse_file, f, root): f for f in py_files}

            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        module_name, imports, tree = result

                        self.nodes[module_name] = DependencyNode(
                            name=module_name,
                            path=file_path,
                            imports=imports,
                            tree=tree,
                        )

                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    def _parse_file(self, path: Path, root: Path) -> tuple[str, set[str], ast.Module] | None:
        try:
            source = path.read_text()
            tree = ast.parse(source)

            try:
                rel_path = path.relative_to(root)
            except ValueError:
                rel_path = path

            parts = list(rel_path.parts)
            if parts and parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            module_name = ".".join(parts)

            imports = self._extract_imports(tree)

            return module_name, imports, tree

        except SyntaxError:
            return None
        except OSError:
            return None

    def _extract_imports(self, tree: ast.Module) -> set[str]:
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        return imports

    def get_imports(self, module_name: str) -> Set[str]:
        node = self.nodes.get(module_name)
        return node.imports if node else set()

    def get_ast(self, module_name: str) -> ast.Module | None:
        node = self.nodes.get(module_name)
        return node.tree if node else None

    def get_dependents(self, module_name: str) -> set[str]:
        dependents: set[str] = set()
        for name, node in self.nodes.items():
            if module_name in node.imports:
                dependents.add(name)
        return dependents

    def topological_order(self) -> list[str]:
        in_degree: dict[str, int] = {}

        for name, node in self.nodes.items():
            internal_imports = sum(1 for imp in node.imports if imp in self.nodes)
            in_degree[name] = internal_imports

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for name, node in self.nodes.items():
                if current in node.imports:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(result) != len(self.nodes):
            remaining = set(self.nodes.keys()) - set(result)
            raise ValueError(f"Circular dependency detected in: {remaining}")

        return result

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, module_name: str) -> bool:
        return module_name in self.nodes
