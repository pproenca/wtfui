import ast


def split_server_client(source: str) -> tuple[str, str]:
    tree = ast.parse(source)

    server_nodes: list[ast.stmt] = []
    client_nodes: list[ast.stmt] = []
    server_imports: list[ast.stmt] = []
    client_imports: list[ast.stmt] = []

    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            if _is_rpc_import(node):
                server_imports.append(node)
            if _is_component_import(node) or _is_ui_import(node):
                client_imports.append(node)

            continue

        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            if _has_decorator(node, "rpc"):
                server_nodes.append(node)
            elif _has_decorator(node, "component"):
                client_nodes.append(node)
            else:
                client_nodes.append(node)
        elif isinstance(node, ast.ClassDef):
            client_nodes.append(node)
        else:
            client_nodes.append(node)

    server_code = _unparse_nodes(server_imports + server_nodes)
    client_code = _unparse_nodes(client_imports + client_nodes)

    return server_code, client_code


def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == name:
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == name:
                return True
    return False


def _is_rpc_import(node: ast.stmt) -> bool:
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and "rpc" in node.module
    return False


def _is_component_import(node: ast.stmt) -> bool:
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
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and ".ui" in node.module
    return False


def _unparse_nodes(nodes: list[ast.stmt]) -> str:
    if not nodes:
        return ""

    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)

    return ast.unparse(module)
