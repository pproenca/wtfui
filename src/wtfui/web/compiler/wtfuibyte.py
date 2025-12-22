import ast
import warnings
from typing import ClassVar

from wtfui.web.compiler.css import CSSGenerator
from wtfui.web.compiler.evaluator import (
    DynamicStyleSentinel,
    get_style_repr,
    safe_eval_style,
)
from wtfui.web.compiler.intrinsics import get_intrinsic_id, is_intrinsic
from wtfui.web.compiler.linker import has_rpc_decorator
from wtfui.web.compiler.opcodes import OpCode
from wtfui.web.compiler.optimizer import optimize
from wtfui.web.compiler.registry import ComponentRegistry
from wtfui.web.compiler.writer import BytecodeWriter


class WtfUICompiler(ast.NodeVisitor):
    EXPECTED_STMT_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "Module",
            "If",
            "For",
            "With",
            "FunctionDef",
            "AsyncFunctionDef",
            "Return",
            "ClassDef",
            "Assign",
            "AugAssign",
            "AnnAssign",
            "Expr",
            "Pass",
            "Import",
            "ImportFrom",
            "Try",
            "TryStar",
            "Raise",
            "Assert",
            "Global",
            "Nonlocal",
            "Break",
            "Continue",
        }
    )

    def __init__(
        self,
        strict: bool = False,
        rpc_functions: set[str] | None = None,
    ) -> None:
        self.writer = BytecodeWriter()
        self.signal_map: dict[str, int] = {}
        self.node_id_counter = 0
        self.handler_map: dict[str, str] = {}
        self.css_gen = CSSGenerator()
        self.strict = strict
        self.unhandled_nodes: list[tuple[str, int, int]] = []
        self.registry = ComponentRegistry()
        self.function_registry: dict[str, ast.FunctionDef] = {}
        self._function_depth: int = 0
        self.rpc_functions = rpc_functions
        self._rpc_registry: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def _is_rpc_call(self, func_name: str) -> bool:
        if self.rpc_functions and func_name in self.rpc_functions:
            return True

        return func_name in self._rpc_registry

    def _scan_rpc_functions(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and has_rpc_decorator(
                node
            ):
                self._rpc_registry[node.name] = node

    def generic_visit(self, node: ast.AST) -> None:
        node_type = type(node).__name__
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", 0)

        if node_type not in self.EXPECTED_STMT_TYPES and isinstance(node, ast.stmt):
            self.unhandled_nodes.append((node_type, line, col))

            msg = (
                f"Unsupported statement '{node_type}' at line {line}, column {col}. "
                f"This construct will be skipped in WtfUIByte compilation."
            )

            if self.strict:
                raise NotImplementedError(msg)
            else:
                warnings.warn(msg, stacklevel=2)

        super().generic_visit(node)

    def compile(self, source_code: str) -> bytes:
        tree = ast.parse(source_code)
        tree = optimize(tree)
        self._scan_rpc_functions(tree)
        self.registry.scan(tree)
        self.visit(tree)

        self.writer.emit_op(OpCode.HALT)

        self._emit_deferred_functions()

        return self.writer.finalize()

    def compile_with_css(self, source_code: str) -> tuple[bytes, str]:
        tree = ast.parse(source_code)
        tree = optimize(tree)
        self._scan_rpc_functions(tree)
        self.registry.scan(tree)
        self.visit(tree)

        self.writer.emit_op(OpCode.HALT)

        self._emit_deferred_functions()

        return (self.writer.finalize(), self.css_gen.get_output())

    def compile_full(
        self, source_code: str, filename: str = "<string>"
    ) -> tuple[bytes, str, bytes]:
        self.writer.set_file(filename)

        tree = ast.parse(source_code)
        tree = optimize(tree)
        self._scan_rpc_functions(tree)
        self.registry.scan(tree)
        self.visit(tree)

        self.writer.emit_op(OpCode.HALT)

        self._emit_deferred_functions()

        return (
            self.writer.finalize(),
            self.css_gen.get_output(),
            self.writer.finalize_map(),
        )

    def visit(self, node: ast.AST) -> None:
        if hasattr(node, "lineno") and isinstance(node.lineno, int):
            self.writer.mark_location(node.lineno)
        super().visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        match node:
            case ast.Assign(
                targets=[ast.Name(id=name)],
                value=ast.Call(
                    func=ast.Name(id="Signal"),
                    args=[ast.Constant(value=val)],
                ),
            ):
                sig_id = len(self.signal_map)
                self.signal_map[name] = sig_id

                if isinstance(val, int | float):
                    self.writer.emit_op(OpCode.INIT_SIG_NUM)
                    self.writer.emit_u16(sig_id)
                    self.writer.emit_f64(float(val))
                else:
                    self.writer.emit_op(OpCode.INIT_SIG_STR)
                    self.writer.emit_u16(sig_id)
                    str_id = self.writer.alloc_string(str(val))
                    self.writer.emit_u16(str_id)

            case ast.Assign(
                targets=[ast.Name(id=name)],
                value=ast.Call(func=ast.Name(id="Signal"), args=[ast.List()]),
            ):
                sig_id = len(self.signal_map)
                self.signal_map[name] = sig_id

                self.writer.emit_op(OpCode.INIT_SIG_STR)
                self.writer.emit_u16(sig_id)
                str_id = self.writer.alloc_string("[]")
                self.writer.emit_u16(str_id)

            case _:
                self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.args.args or node.args.posonlyargs or node.args.kwonlyargs:
            raise NotImplementedError(
                f"Function '{node.name}' has parameters. "
                "Function parameters are not supported in WtfUIByte. "
                "Use signals for shared state instead."
            )
        if node.args.vararg or node.args.kwarg:
            raise NotImplementedError(
                f"Function '{node.name}' has *args/**kwargs. "
                "Function parameters are not supported in WtfUIByte."
            )

        if self._function_depth > 0:
            raise NotImplementedError(
                f"Nested function '{node.name}' detected. "
                "Nested functions are not supported in WtfUIByte. "
                "Define all functions at module level."
            )

        self.function_registry[node.name] = node

        label = f"func_{node.name}"
        self.handler_map[node.name] = label

        self._function_depth += 1
        try:
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    self.visit_FunctionDef(stmt)
        finally:
            self._function_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        match node.test:
            case ast.Attribute(value=ast.Name(id=sig_name), attr="value"):
                if sig_name not in self.signal_map:
                    self.generic_visit(node)
                    return

                sig_id = self.signal_map[sig_name]

                lbl_true = f"if_{node.lineno}_true"
                lbl_false = f"if_{node.lineno}_false"
                lbl_end = f"if_{node.lineno}_end"

                self.writer.emit_op(OpCode.DOM_IF)
                self.writer.emit_u16(sig_id)
                self.writer.emit_jump_placeholder(lbl_true)
                self.writer.emit_jump_placeholder(lbl_false)

                self.writer.emit_op(OpCode.JMP)
                self.writer.emit_jump_placeholder(lbl_end)

                self.writer.mark_label(lbl_true)
                for stmt in node.body:
                    self.visit(stmt)
                self.writer.emit_op(OpCode.HALT)

                self.writer.mark_label(lbl_false)
                for stmt in node.orelse:
                    self.visit(stmt)
                self.writer.emit_op(OpCode.HALT)

                self.writer.mark_label(lbl_end)

            case _:
                self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        match node.iter:
            case ast.Attribute(value=ast.Name(id=list_name), attr="value"):
                if list_name not in self.signal_map:
                    self.generic_visit(node)
                    return

                list_sig_id = self.signal_map[list_name]

                match node.target:
                    case ast.Name(id=item_name):
                        item_sig_id = len(self.signal_map)
                        self.signal_map[item_name] = item_sig_id
                    case _:
                        self.generic_visit(node)
                        return

                lbl_template = f"for_{node.lineno}_template"
                lbl_end = f"for_{node.lineno}_end"

                self.writer.emit_op(OpCode.DOM_FOR)
                self.writer.emit_u16(list_sig_id)
                self.writer.emit_u16(item_sig_id)
                self.writer.emit_jump_placeholder(lbl_template)

                self.writer.emit_op(OpCode.JMP)
                self.writer.emit_jump_placeholder(lbl_end)

                self.writer.mark_label(lbl_template)
                for stmt in node.body:
                    self.visit(stmt)
                self.writer.emit_op(OpCode.HALT)

                self.writer.mark_label(lbl_end)

            case _:
                self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        match node:
            case ast.AugAssign(
                target=ast.Attribute(value=ast.Name(id=name), attr="value"),
                op=op,
                value=operand,
            ) if name in self.signal_map:
                sig_id = self.signal_map[name]

                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

                self._compile_expr(operand)

                self._emit_binop(op)

                self.writer.emit_op(OpCode.STORE_SIG)
                self.writer.emit_u16(sig_id)

            case _:
                self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self._compile_expr(node)

        self.writer.emit_op(OpCode.POP)
        self.writer.emit_u8(1)

    def visit_Compare(self, node: ast.Compare) -> None:
        self._compile_expr(node)

        self.writer.emit_op(OpCode.POP)
        self.writer.emit_u8(1)

    def _compile_expr(self, node: ast.expr) -> None:
        match node:
            case ast.Constant(value=val) if isinstance(val, int | float):
                self.writer.emit_op(OpCode.PUSH_NUM)
                self.writer.emit_f64(float(val))

            case ast.Constant(value=val) if isinstance(val, str):
                str_id = self.writer.alloc_string(val)
                self.writer.emit_op(OpCode.PUSH_STR)
                self.writer.emit_u16(str_id)

            case ast.Attribute(value=ast.Name(id=name), attr="value") if name in self.signal_map:
                sig_id = self.signal_map[name]
                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

            case ast.BinOp(left=left, op=op, right=right):
                self._compile_expr(left)
                self._compile_expr(right)
                self._emit_binop(op)

            case ast.Compare(left=left, ops=[op], comparators=[right]):
                self._compile_expr(left)
                self._compile_expr(right)
                self._emit_compare(op)

            case ast.Call(func=ast.Name(id=func_name), args=args) if self._is_rpc_call(func_name):
                self._compile_rpc_call(func_name, args)

            case ast.Call(func=ast.Name(id=func_name), args=args):
                if is_intrinsic(func_name):
                    self._compile_intrinsic_call(func_name, args)
                elif func_name in self.function_registry:
                    self.writer.emit_op(OpCode.CALL)
                    label = f"func_{func_name}"
                    self.writer.emit_jump_placeholder(label)

            case ast.Name(id=name) if name in self.signal_map:
                sig_id = self.signal_map[name]
                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

            case _:
                pass

    def _emit_binop(self, op: ast.operator) -> None:
        match op:
            case ast.Add():
                self.writer.emit_op(OpCode.ADD_STACK)
            case ast.Sub():
                self.writer.emit_op(OpCode.SUB_STACK)
            case ast.Mult():
                self.writer.emit_op(OpCode.MUL)
            case ast.Div():
                self.writer.emit_op(OpCode.DIV)
            case ast.Mod():
                self.writer.emit_op(OpCode.MOD)
            case _:
                pass

    def _emit_compare(self, op: ast.cmpop) -> None:
        match op:
            case ast.Eq():
                self.writer.emit_op(OpCode.EQ)
            case ast.NotEq():
                self.writer.emit_op(OpCode.NE)
            case ast.Lt():
                self.writer.emit_op(OpCode.LT)
            case ast.LtE():
                self.writer.emit_op(OpCode.LE)
            case ast.Gt():
                self.writer.emit_op(OpCode.GT)
            case ast.GtE():
                self.writer.emit_op(OpCode.GE)
            case _:
                pass

    def _compile_intrinsic_call(self, func_name: str, args: list[ast.expr]) -> None:
        intrinsic_id = get_intrinsic_id(func_name)
        if intrinsic_id is None:
            return

        for arg in args:
            self._compile_expr(arg)

        self.writer.emit_op(OpCode.CALL_INTRINSIC)
        self.writer.emit_u8(intrinsic_id)
        self.writer.emit_u8(len(args))

    def _compile_rpc_call(self, func_name: str, args: list[ast.expr]) -> None:
        result_sig_id = len(self.signal_map)
        sig_name = f"_rpc_result_{func_name}_{result_sig_id}"
        self.signal_map[sig_name] = result_sig_id

        empty_str_id = self.writer.alloc_string("")
        self.writer.emit_op(OpCode.INIT_SIG_STR)
        self.writer.emit_u16(result_sig_id)
        self.writer.emit_u16(empty_str_id)

        for arg in args:
            self._compile_expr(arg)

        func_str_id = self.writer.alloc_string(func_name)

        self.writer.emit_op(OpCode.RPC_CALL)
        self.writer.emit_u16(func_str_id)
        self.writer.emit_u16(result_sig_id)
        self.writer.emit_u8(len(args))

        self.writer.emit_op(OpCode.LOAD_SIG)
        self.writer.emit_u16(result_sig_id)

    def visit_With(self, node: ast.With) -> None:
        match node:
            case ast.With(
                items=[
                    ast.withitem(context_expr=ast.Call(func=ast.Name(id=tag), keywords=keywords))
                ],
                body=body,
            ):
                node_id = self.node_id_counter
                self.node_id_counter += 1

                tag_str = self.writer.alloc_string(tag.lower())
                self.writer.emit_op(OpCode.DOM_CREATE)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(tag_str)

                self._emit_element_attributes(node_id, keywords)

                self.writer.emit_op(OpCode.DOM_APPEND)
                self.writer.emit_u16(0)
                self.writer.emit_u16(node_id)

                for child in body:
                    self.visit(child)

            case ast.With(
                items=[ast.withitem(context_expr=ast.Call(func=ast.Name(id=tag)))],
                body=body,
            ):
                node_id = self.node_id_counter
                self.node_id_counter += 1

                tag_str = self.writer.alloc_string(tag.lower())
                self.writer.emit_op(OpCode.DOM_CREATE)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(tag_str)

                self.writer.emit_op(OpCode.DOM_APPEND)
                self.writer.emit_u16(0)
                self.writer.emit_u16(node_id)

                for child in body:
                    self.visit(child)

            case _:
                self.generic_visit(node)

    def _emit_element_attributes(self, node_id: int, keywords: list[ast.keyword]) -> None:
        for kw in keywords:
            match kw:
                case ast.keyword(arg="class_" | "cls", value=ast.Constant(value=class_val)):
                    class_str = self.writer.alloc_string(str(class_val))
                    self.writer.emit_op(OpCode.DOM_ATTR_CLASS)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(class_str)

                case ast.keyword(arg="id", value=ast.Constant(value=id_val)):
                    attr_str = self.writer.alloc_string("id")
                    val_str = self.writer.alloc_string(str(id_val))
                    self.writer.emit_op(OpCode.DOM_ATTR)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(attr_str)
                    self.writer.emit_u16(val_str)

                case ast.keyword(arg="on_click", value=ast.Name(id=handler_name)):
                    if handler_name in self.function_registry:
                        self.writer.emit_op(OpCode.DOM_ON_CLICK)
                        self.writer.emit_u16(node_id)
                        label = f"func_{handler_name}"
                        self.writer.emit_jump_placeholder(label)
                    elif self.strict:
                        raise NotImplementedError(
                            f"on_click handler '{handler_name}' not found in local scope. "
                            "Only locally-defined functions are supported. "
                            "Imported handlers require Linker support (not yet implemented)."
                        )
                    else:
                        warnings.warn(
                            f"on_click handler '{handler_name}' not in local function_registry. "
                            "Emitting placeholder address 0. Handler will not work at runtime.",
                            stacklevel=2,
                        )
                        self.writer.emit_op(OpCode.DOM_ON_CLICK)
                        self.writer.emit_u16(node_id)
                        self.writer.emit_u32(0)

                case ast.keyword(arg="style", value=style_node):
                    style_result = safe_eval_style(style_node)
                    if isinstance(style_result, DynamicStyleSentinel):
                        self._emit_dynamic_style_evaluated(node_id, style_node)
                    else:
                        self._emit_static_styles_from_dict(node_id, style_result)

                case _:
                    if kw.arg and isinstance(kw.value, ast.Constant):
                        attr_str = self.writer.alloc_string(kw.arg.replace("_", "-"))
                        val_str = self.writer.alloc_string(str(kw.value.value))
                        self.writer.emit_op(OpCode.DOM_ATTR)
                        self.writer.emit_u16(node_id)
                        self.writer.emit_u16(attr_str)
                        self.writer.emit_u16(val_str)

    def _emit_static_styles(
        self, node_id: int, keys: list[ast.expr | None], values: list[ast.expr]
    ) -> None:
        for key, value in zip(keys, values, strict=True):
            match (key, value):
                case (ast.Constant(value=prop), ast.Constant(value=val)):
                    prop_str = self.writer.alloc_string(str(prop))
                    val_str = self.writer.alloc_string(str(val))
                    self.writer.emit_op(OpCode.DOM_STYLE_STATIC)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(prop_str)
                    self.writer.emit_u16(val_str)

                case (ast.Constant(value=prop), expr):
                    prop_str = self.writer.alloc_string(str(prop))
                    self._compile_expr(expr)
                    self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(prop_str)

                case _:
                    pass

    def _emit_style_string(self, node_id: int, style_str: str) -> None:
        for declaration in style_str.split(";"):
            declaration = declaration.strip()
            if ":" in declaration:
                prop, val = declaration.split(":", 1)
                prop_str = self.writer.alloc_string(prop.strip())
                val_str = self.writer.alloc_string(val.strip())
                self.writer.emit_op(OpCode.DOM_STYLE_STATIC)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(prop_str)
                self.writer.emit_u16(val_str)

    def _emit_static_styles_from_dict(self, node_id: int, style_dict: dict[str, object]) -> None:
        class_name = self.css_gen.register(style_dict)

        class_str_id = self.writer.alloc_string(class_name)
        self.writer.emit_op(OpCode.DOM_ATTR_CLASS)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(class_str_id)

    def _emit_dynamic_style_evaluated(self, node_id: int, style_node: ast.expr) -> None:
        style_repr = get_style_repr(style_node)
        style_str_id = self.writer.alloc_string(style_repr)

        prop_str = self.writer.alloc_string("cssText")
        self.writer.emit_op(OpCode.PUSH_STR)
        self.writer.emit_u16(style_str_id)
        self.writer.emit_op(OpCode.DOM_STYLE_DYN)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(prop_str)

    def _emit_dynamic_style(self, node_id: int, expr: ast.expr) -> None:
        match expr:
            case ast.JoinedStr():
                self._compile_expr(expr)

                prop_str = self.writer.alloc_string("cssText")
                self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(prop_str)

            case _:
                self._compile_expr(expr)
                prop_str = self.writer.alloc_string("cssText")
                self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(prop_str)

    def visit_Expr(self, node: ast.Expr) -> None:
        match node.value:
            case ast.Call(
                func=ast.Name(id="Text"),
                args=[ast.Constant(value=text)],
            ):
                self._emit_text_element(str(text))

            case ast.Call(
                func=ast.Name(id="Button"),
                args=[ast.Constant(value=label)],
                keywords=keywords,
            ):
                self._emit_button_element(str(label), keywords)

            case ast.Call(func=ast.Name(id=func_name), args=args) if self._is_rpc_call(func_name):
                self._compile_rpc_call(func_name, args)

                self.writer.emit_op(OpCode.POP)
                self.writer.emit_u8(1)

            case ast.Call(func=ast.Name(id=func_name), args=args) if is_intrinsic(func_name):
                self._compile_intrinsic_call(func_name, args)

            case ast.Call(func=ast.Name(id=func_name)) if func_name in self.registry:
                self._inline_component(func_name)

            case ast.Call(func=ast.Name(id=func_name)) if func_name in self.function_registry:
                self.writer.emit_op(OpCode.CALL)
                label = f"func_{func_name}"
                self.writer.emit_jump_placeholder(label)

            case _:
                self.generic_visit(node)

    def _emit_text_element(self, text: str) -> None:
        node_id = self.node_id_counter
        self.node_id_counter += 1

        span_str = self.writer.alloc_string("span")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(span_str)

        text_str = self.writer.alloc_string(text)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(text_str)

        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)

    def _emit_button_element(self, label: str, keywords: list[ast.keyword]) -> None:
        node_id = self.node_id_counter
        self.node_id_counter += 1

        btn_str = self.writer.alloc_string("button")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(btn_str)

        label_str = self.writer.alloc_string(label)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(label_str)

        for kw in keywords:
            if kw.arg == "on_click" and isinstance(kw.value, ast.Name):
                handler_name = kw.value.id

                if handler_name in self.function_registry:
                    self.writer.emit_op(OpCode.DOM_ON_CLICK)
                    self.writer.emit_u16(node_id)
                    label = f"func_{handler_name}"
                    self.writer.emit_jump_placeholder(label)
                elif self.strict:
                    raise NotImplementedError(
                        f"on_click handler '{handler_name}' not found in local scope. "
                        "Only locally-defined functions are supported. "
                        "Imported handlers require Linker support (not yet implemented)."
                    )
                else:
                    warnings.warn(
                        f"on_click handler '{handler_name}' not in local function_registry. "
                        "Emitting placeholder address 0. Handler will not work at runtime.",
                        stacklevel=2,
                    )
                    self.writer.emit_op(OpCode.DOM_ON_CLICK)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u32(0)

        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)

    def _inline_component(self, name: str) -> None:
        body = self.registry.get_body(name)
        if body is None:
            return

        for stmt in body:
            self.visit(stmt)

    def _emit_deferred_functions(self) -> None:
        for name, node in self.function_registry.items():
            label = f"func_{name}"
            self.writer.mark_label(label)

            for stmt in node.body:
                self.visit(stmt)

            self.writer.emit_op(OpCode.RET)


def compile_to_wtfuibyte(source: str) -> bytes:
    compiler = WtfUICompiler()
    return compiler.compile(source)
