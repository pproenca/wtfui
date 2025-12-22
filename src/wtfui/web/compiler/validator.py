"""Bundle optimization validator for detecting client/server boundary crossings.

This module provides validation tools for bundle optimization, ensuring
client code doesn't accidentally import server-only modules.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.web.compiler.analyzer import SplitBrainAnalyzer
    from wtfui.web.compiler.graph import DependencyGraph


@dataclass(frozen=True)
class SecurityViolation:
    client_module: str
    server_module: str
    message: str

    def __str__(self) -> str:
        return self.message


class BoundarySentinelError(Exception):
    def __init__(self, violations: list[SecurityViolation]) -> None:
        self.violations = violations
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = ["Bundle boundary violations detected:", ""]
        for v in self.violations:
            lines.append(f"  • {v}")
        lines.append("")
        lines.append("Client modules cannot directly import server modules.")
        lines.append("Use @rpc decorated functions and RPC calls instead.")
        return "\n".join(lines)


class BoundarySentinel:
    """Validates client/server boundary crossings for bundle optimization.

    WARNING: This is NOT a security boundary. It helps optimize bundle size
    by detecting accidental imports, but does not enforce security isolation.
    Server secrets must never be in client-reachable code.
    """

    def __init__(
        self,
        graph: DependencyGraph,
        analyzer: SplitBrainAnalyzer,
    ) -> None:
        self.graph = graph
        self.analyzer = analyzer
        self._violations: list[SecurityViolation] = []

    def validate(self) -> None:
        violations = self.check()
        if violations:
            raise BoundarySentinelError(violations)

    def check(self) -> list[SecurityViolation]:
        self._violations = []

        from wtfui.web.compiler.analyzer import ModuleType

        for module_name in self.analyzer.get_client_modules():
            node = self.graph.nodes.get(module_name)
            if node is None:
                continue

            for imported in node.imports:
                if imported not in self.graph.nodes:
                    continue

                imported_type = self.analyzer.get_type(imported)

                if imported_type == ModuleType.SERVER:
                    self._violations.append(
                        SecurityViolation(
                            client_module=module_name,
                            server_module=imported,
                            message=(
                                f"Client module '{module_name}' cannot import "
                                f"server module '{imported}'"
                            ),
                        )
                    )

        return self._violations

    def check_single(self, module_name: str) -> list[SecurityViolation]:
        from wtfui.web.compiler.analyzer import ModuleType

        violations: list[SecurityViolation] = []

        module_type = self.analyzer.get_type(module_name)
        if module_type != ModuleType.CLIENT:
            return []

        node = self.graph.nodes.get(module_name)
        if node is None:
            return []

        for imported in node.imports:
            if imported not in self.graph.nodes:
                continue

            imported_type = self.analyzer.get_type(imported)

            if imported_type == ModuleType.SERVER:
                violations.append(
                    SecurityViolation(
                        client_module=module_name,
                        server_module=imported,
                        message=(
                            f"Client module '{module_name}' cannot import "
                            f"server module '{imported}'"
                        ),
                    )
                )

        return violations

    def get_allowed_imports(self, module_name: str) -> set[str]:
        from wtfui.web.compiler.analyzer import ModuleType

        node = self.graph.nodes.get(module_name)
        if node is None:
            return set()

        module_type = self.analyzer.get_type(module_name)

        if module_type == ModuleType.SERVER:
            return node.imports

        allowed: set[str] = set()
        for imported in node.imports:
            if imported not in self.graph.nodes:
                allowed.add(imported)
                continue

            imported_type = self.analyzer.get_type(imported)
            if imported_type != ModuleType.SERVER:
                allowed.add(imported)

        return allowed

    def get_rpc_candidates(self, module_name: str) -> set[str]:
        from wtfui.web.compiler.analyzer import ModuleType

        module_type = self.analyzer.get_type(module_name)
        if module_type != ModuleType.CLIENT:
            return set()

        node = self.graph.nodes.get(module_name)
        if node is None:
            return set()

        rpc_needed: set[str] = set()
        for imported in node.imports:
            if imported not in self.graph.nodes:
                continue

            imported_type = self.analyzer.get_type(imported)
            if imported_type == ModuleType.SERVER:
                rpc_needed.add(imported)

        return rpc_needed
