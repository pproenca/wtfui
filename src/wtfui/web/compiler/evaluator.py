import ast
from typing import Any


class DynamicStyleSentinel:
    __slots__ = ()

    def __repr__(self) -> str:
        return "DYNAMIC_STYLE"


DYNAMIC_STYLE = DynamicStyleSentinel()


THEME_REGISTRY: dict[tuple[str, ...], str] = {
    ("Colors", "Blue", "_50"): "#eff6ff",
    ("Colors", "Blue", "_100"): "#dbeafe",
    ("Colors", "Blue", "_200"): "#bfdbfe",
    ("Colors", "Blue", "_300"): "#93c5fd",
    ("Colors", "Blue", "_400"): "#60a5fa",
    ("Colors", "Blue", "_500"): "#3b82f6",
    ("Colors", "Blue", "_600"): "#2563eb",
    ("Colors", "Blue", "_700"): "#1d4ed8",
    ("Colors", "Blue", "_800"): "#1e40af",
    ("Colors", "Blue", "_900"): "#1e3a8a",
    ("Colors", "Red", "_50"): "#fef2f2",
    ("Colors", "Red", "_100"): "#fee2e2",
    ("Colors", "Red", "_200"): "#fecaca",
    ("Colors", "Red", "_300"): "#fca5a5",
    ("Colors", "Red", "_400"): "#f87171",
    ("Colors", "Red", "_500"): "#ef4444",
    ("Colors", "Red", "_600"): "#dc2626",
    ("Colors", "Red", "_700"): "#b91c1c",
    ("Colors", "Red", "_800"): "#991b1b",
    ("Colors", "Red", "_900"): "#7f1d1d",
    ("Colors", "Green", "_50"): "#f0fdf4",
    ("Colors", "Green", "_100"): "#dcfce7",
    ("Colors", "Green", "_200"): "#bbf7d0",
    ("Colors", "Green", "_300"): "#86efac",
    ("Colors", "Green", "_400"): "#4ade80",
    ("Colors", "Green", "_500"): "#22c55e",
    ("Colors", "Green", "_600"): "#16a34a",
    ("Colors", "Green", "_700"): "#15803d",
    ("Colors", "Green", "_800"): "#166534",
    ("Colors", "Green", "_900"): "#14532d",
    ("Colors", "Slate", "_50"): "#f8fafc",
    ("Colors", "Slate", "_100"): "#f1f5f9",
    ("Colors", "Slate", "_200"): "#e2e8f0",
    ("Colors", "Slate", "_300"): "#cbd5e1",
    ("Colors", "Slate", "_400"): "#94a3b8",
    ("Colors", "Slate", "_500"): "#64748b",
    ("Colors", "Slate", "_600"): "#475569",
    ("Colors", "Slate", "_700"): "#334155",
    ("Colors", "Slate", "_800"): "#1e293b",
    ("Colors", "Slate", "_900"): "#0f172a",
    ("Colors", "White"): "#ffffff",
    ("Colors", "Black"): "#000000",
    ("Colors", "Transparent"): "transparent",
}


def safe_eval_style(node: ast.AST) -> dict[str, Any] | DynamicStyleSentinel:
    try:
        return _try_static_eval(node)
    except ValueError, AttributeError, KeyError, TypeError:
        return DYNAMIC_STYLE


def _try_static_eval(node: ast.AST) -> dict[str, Any]:
    if isinstance(node, ast.Call):
        if _is_name(node.func, "Style"):
            props: dict[str, Any] = {}
            for kw in node.keywords:
                if kw.arg is None:
                    raise ValueError("**kwargs in style not supported")

                val = _eval_value(kw.value)
                if isinstance(val, DynamicStyleSentinel):
                    raise ValueError("Dynamic value in style")
                props[kw.arg] = val
            return props
        else:
            raise ValueError(f"Function call in style: {ast.unparse(node)}")

    elif isinstance(node, ast.Dict):
        props = {}
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None:
                raise ValueError("Dict spread in style not supported")
            key_val = _eval_value(key)
            val = _eval_value(value)
            if isinstance(key_val, DynamicStyleSentinel) or isinstance(val, DynamicStyleSentinel):
                raise ValueError("Dynamic value in style dict")
            props[key_val] = val
        return props

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return _parse_css_string(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    raise ValueError(f"Unsupported style node: {type(node)}")


def _eval_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    elif isinstance(node, ast.Attribute):
        return _resolve_static_attribute(node)

    elif isinstance(node, ast.Name):
        raise ValueError(f"Variable reference: {node.id}")

    elif isinstance(node, ast.Call):
        raise ValueError("Function call in style value")

    elif isinstance(node, ast.BinOp):
        raise ValueError("Binary operation in style value")

    elif isinstance(node, ast.JoinedStr):
        raise ValueError("f-string in style value")

    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            if isinstance(node.operand.value, int | float):
                return -node.operand.value
            raise ValueError("Unary minus on non-numeric constant")
        raise ValueError("Unsupported unary operation")

    raise ValueError(f"Unsupported value node: {type(node)}")


def _resolve_static_attribute(node: ast.Attribute) -> str:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.insert(0, current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.insert(0, current.id)

    key = tuple(parts)
    if key in THEME_REGISTRY:
        return THEME_REGISTRY[key]

    raise ValueError(f"Unknown theme reference: {'.'.join(parts)}")


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _parse_css_string(css: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for declaration in css.split(";"):
        declaration = declaration.strip()
        if ":" in declaration:
            prop, val = declaration.split(":", 1)
            props[prop.strip()] = val.strip()
    return props


def is_static_style(node: ast.AST) -> bool:
    result = safe_eval_style(node)
    return not isinstance(result, DynamicStyleSentinel)


def get_style_repr(node: ast.AST) -> str:
    return ast.unparse(node)
