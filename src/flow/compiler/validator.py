"""BoundarySentinel - Security Firewall for Client/Server Boundary.

Validates that client code does not directly import server modules.
This is critical for security: client code runs in the browser and
MUST NOT have access to server-side secrets, database connections,
or file system operations.

Security Model:
- CLIENT modules can ONLY access SERVER modules via RPC
- Direct imports from CLIENT → SERVER are compilation errors
- SHARED modules can be imported by both CLIENT and SERVER

Pipeline Position:
    SplitBrainAnalyzer → [BoundarySentinel] → Linker

Violation Examples:
    # ERROR: Direct import of server module in client code
    from myapp.api import fetch_users  # Contains @rpc or DB access

    # OK: Using RPC call instead
    result = rpc.fetch_users()  # Will be compiled to RPC_CALL opcode
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow.compiler.analyzer import SplitBrainAnalyzer
    from flow.compiler.graph import DependencyGraph


@dataclass(frozen=True)
class SecurityViolation:
    """Represents a security boundary violation.

    Attributes:
        client_module: Module that attempted the illegal import
        server_module: Server module that was imported
        message: Human-readable error message
    """

    client_module: str
    server_module: str
    message: str

    def __str__(self) -> str:
        return self.message


class BoundarySentinelError(Exception):
    """Raised when security boundary violations are detected.

    Contains a list of all violations found during validation.
    """

    def __init__(self, violations: list[SecurityViolation]) -> None:
        self.violations = violations
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format all violations into a readable error message."""
        lines = ["Security boundary violations detected:", ""]
        for v in self.violations:
            lines.append(f"  • {v}")
        lines.append("")
        lines.append("Client modules cannot directly import server modules.")
        lines.append("Use @rpc decorated functions and RPC calls instead.")
        return "\n".join(lines)


class BoundarySentinel:
    """Security firewall for client/server boundary.

    Validates that client-side code does not directly import
    server-side modules. This prevents security leaks where
    client code could access database connections, secrets,
    or file system operations.

    Example:
        graph = DependencyGraph()
        graph.build_parallel(Path("src/myapp"))

        analyzer = SplitBrainAnalyzer(graph)
        analyzer.analyze()

        sentinel = BoundarySentinel(graph, analyzer)

        # Will raise BoundarySentinelError if violations found
        sentinel.validate()

        # Or check without raising
        violations = sentinel.check()
        if violations:
            for v in violations:
                print(f"Error: {v}")
    """

    def __init__(
        self,
        graph: DependencyGraph,
        analyzer: SplitBrainAnalyzer,
    ) -> None:
        """Initialize sentinel with graph and analyzer.

        Args:
            graph: Dependency graph with module relationships
            analyzer: Module type classifications
        """
        self.graph = graph
        self.analyzer = analyzer
        self._violations: list[SecurityViolation] = []

    def validate(self) -> None:
        """Validate all client modules and raise on violations.

        Raises:
            BoundarySentinelError: If any security violations found
        """
        violations = self.check()
        if violations:
            raise BoundarySentinelError(violations)

    def check(self) -> list[SecurityViolation]:
        """Check all client modules for security violations.

        Returns a list of violations (empty if all checks pass).

        Returns:
            List of SecurityViolation objects
        """
        self._violations = []

        # Import here to avoid circular imports
        from flow.compiler.analyzer import ModuleType

        # Check each client module's imports
        for module_name in self.analyzer.get_client_modules():
            node = self.graph.nodes.get(module_name)
            if node is None:
                continue

            for imported in node.imports:
                # Skip if not in our graph (external package)
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
        """Check a single module for security violations.

        Useful for incremental validation during development.

        Args:
            module_name: Module to check

        Returns:
            List of violations for this module
        """
        # Import here to avoid circular imports
        from flow.compiler.analyzer import ModuleType

        violations: list[SecurityViolation] = []

        module_type = self.analyzer.get_type(module_name)
        if module_type != ModuleType.CLIENT:
            return []  # Only check client modules

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
        """Get imports that are allowed for a module.

        Filters out any server modules if this is a client module.

        Args:
            module_name: Module to check

        Returns:
            Set of allowed import names
        """
        # Import here to avoid circular imports
        from flow.compiler.analyzer import ModuleType

        node = self.graph.nodes.get(module_name)
        if node is None:
            return set()

        module_type = self.analyzer.get_type(module_name)

        # Server modules can import anything
        if module_type == ModuleType.SERVER:
            return node.imports

        # Client/Shared modules cannot import server modules
        allowed: set[str] = set()
        for imported in node.imports:
            if imported not in self.graph.nodes:
                # External package - allow (will be bundled or errored elsewhere)
                allowed.add(imported)
                continue

            imported_type = self.analyzer.get_type(imported)
            if imported_type != ModuleType.SERVER:
                allowed.add(imported)

        return allowed

    def get_rpc_candidates(self, module_name: str) -> set[str]:
        """Get imports that should be converted to RPC calls.

        These are server modules that a client module is trying to use.
        Instead of direct import, these should use RPC.

        Args:
            module_name: Client module name

        Returns:
            Set of server module names that need RPC conversion
        """
        # Import here to avoid circular imports
        from flow.compiler.analyzer import ModuleType

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
