import ast
import operator
from typing import Any, ClassVar


class ConstantFolder(ast.NodeTransformer):
    BINARY_OPS: ClassVar[dict[type, Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    COMPARE_OPS: ClassVar[dict[type, Any]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    UNARY_OPS: ClassVar[dict[type, Any]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
    }

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.BinOp):
            return visited

        if isinstance(visited.left, ast.Constant) and isinstance(visited.right, ast.Constant):
            op_func = self.BINARY_OPS.get(type(visited.op))
            if op_func is not None:
                try:
                    result = op_func(visited.left.value, visited.right.value)
                    return ast.Constant(value=result)
                except ZeroDivisionError, TypeError, OverflowError:
                    pass

        return visited

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.Compare):
            return visited

        if (
            len(visited.ops) == 1
            and len(visited.comparators) == 1
            and isinstance(visited.left, ast.Constant)
            and isinstance(visited.comparators[0], ast.Constant)
        ):
            op_func = self.COMPARE_OPS.get(type(visited.ops[0]))
            if op_func is not None:
                try:
                    result = op_func(visited.left.value, visited.comparators[0].value)
                    return ast.Constant(value=result)
                except TypeError:
                    pass

        return visited

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.UnaryOp):
            return visited

        if isinstance(visited.operand, ast.Constant):
            op_func = self.UNARY_OPS.get(type(visited.op))
            if op_func is not None:
                try:
                    result = op_func(visited.operand.value)
                    return ast.Constant(value=result)
                except TypeError:
                    pass

        return visited


class DeadCodeEliminator(ast.NodeTransformer):
    def visit_If(self, node: ast.If) -> ast.AST | list[ast.stmt]:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.If):
            return visited

        if isinstance(visited.test, ast.Constant):
            if visited.test.value:
                return visited.body
            else:
                if visited.orelse:
                    return visited.orelse
                else:
                    return []

        return visited

    def visit_Module(self, node: ast.Module) -> ast.Module:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.Module):
            return node
        visited.body = self._filter_pass(visited.body, keep_if_empty=False)
        return visited

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.FunctionDef):
            return node
        visited.body = self._filter_pass(visited.body, keep_if_empty=True)
        return visited

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.AsyncFunctionDef):
            return node
        visited.body = self._filter_pass(visited.body, keep_if_empty=True)
        return visited

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        visited = self.generic_visit(node)
        if not isinstance(visited, ast.ClassDef):
            return node
        visited.body = self._filter_pass(visited.body, keep_if_empty=True)
        return visited

    def _filter_pass(self, stmts: list[ast.stmt], keep_if_empty: bool) -> list[ast.stmt]:
        flat: list[ast.stmt] = []
        for stmt in stmts:
            if isinstance(stmt, list):
                flat.extend(stmt)
            else:
                flat.append(stmt)

        filtered = [s for s in flat if not isinstance(s, ast.Pass)]

        if keep_if_empty and not filtered:
            return [ast.Pass()]

        return filtered if filtered else flat[:0]


def optimize[AstT: ast.AST](tree: AstT) -> AstT:
    folder = ConstantFolder()
    tree = folder.visit(tree)

    eliminator = DeadCodeEliminator()
    tree = eliminator.visit(tree)

    ast.fix_missing_locations(tree)

    return tree
