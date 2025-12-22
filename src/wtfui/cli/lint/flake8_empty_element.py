import ast
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Generator


ELEMENT_NAMES: set[str] = {
    "Element",
    "Div",
    "Span",
    "VStack",
    "HStack",
    "Flex",
    "Box",
    "Button",
    "Input",
    "Text",
    "Card",
    "Window",
    "Section",
    "Panel",
    "Modal",
}


class EmptyElementChecker(ast.NodeVisitor):
    name: ClassVar[str] = "flake8-fuse-empty-element"
    version: ClassVar[str] = "1.0.0"

    def __init__(self, tree: ast.AST, filename: str = "") -> None:
        self.tree = tree
        self.filename = filename
        self.errors: list[tuple[int, int, str, type[EmptyElementChecker]]] = []

    def run(self) -> Generator[tuple[int, int, str, type[EmptyElementChecker]]]:
        self.visit(self.tree)
        yield from self.errors

    def visit_With(self, node: ast.With) -> None:
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    elem_name = _extract_name(item.context_expr.func)
                    if elem_name in ELEMENT_NAMES:
                        self.errors.append(
                            (
                                node.lineno,
                                node.col_offset,
                                f"FLE001 Empty {elem_name}() - use `{elem_name}(...)` "
                                f"instead of `with {elem_name}(...): pass`",
                                type(self),
                            )
                        )

                        break

        self.generic_visit(node)


def _extract_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
