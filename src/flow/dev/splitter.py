# src/flow/dev/splitter.py
"""AST Splitter - Zero-Build Developer Experience.

Splits a single source file into:
- Server code: @rpc decorated functions
- Client code: @component decorated functions and UI code

This enables single-file development where the framework
automatically separates concerns for SSR + Wasm deployment.
"""

from __future__ import annotations

import ast


def split_server_client(source: str) -> tuple[str, str]:
    """
    Split source code into server and client portions.

    Server code: Functions decorated with @rpc
    Client code: Everything else (components, UI elements)

    Args:
        source: Python source code

    Returns:
        Tuple of (server_code, client_code)
    """
    tree = ast.parse(source)

    server_nodes: list[ast.stmt] = []
    client_nodes: list[ast.stmt] = []
    server_imports: list[ast.stmt] = []
    client_imports: list[ast.stmt] = []

    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            # Track imports for both sides
            if _is_rpc_import(node):
                server_imports.append(node)
            if _is_component_import(node) or _is_ui_import(node):
                client_imports.append(node)
            # Both get shared imports
            continue

        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            if _has_decorator(node, "rpc"):
                server_nodes.append(node)
            elif _has_decorator(node, "component"):
                client_nodes.append(node)
            else:
                # Undecorated goes to client by default
                client_nodes.append(node)
        elif isinstance(node, ast.ClassDef):
            client_nodes.append(node)
        else:
            # Other statements (assignments, etc.) go to both
            client_nodes.append(node)

    # Reassemble the code
    server_code = _unparse_nodes(server_imports + server_nodes)
    client_code = _unparse_nodes(client_imports + client_nodes)

    return server_code, client_code


def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Check if a function has a specific decorator."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == name:
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == name:
                return True
    return False


def _is_rpc_import(node: ast.stmt) -> bool:
    """Check if an import statement imports rpc."""
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and "rpc" in node.module
    return False


def _is_component_import(node: ast.stmt) -> bool:
    """Check if an import statement imports component."""
    if isinstance(node, ast.ImportFrom):
        if node.module is None:
            return False
        if "component" in node.module:
            return True
        for alias in node.names:
            if alias.name == "component":
                return True
    return False


def _is_ui_import(node: ast.stmt) -> bool:
    """Check if an import statement imports UI elements."""
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and ".ui" in node.module
    return False


def _unparse_nodes(nodes: list[ast.stmt]) -> str:
    """Convert AST nodes back to source code."""
    if not nodes:
        return ""

    # Create a module with just these nodes
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)

    return ast.unparse(module)
