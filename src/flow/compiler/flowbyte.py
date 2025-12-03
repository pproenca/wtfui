"""FlowByte AST Compiler - Python to bytecode transformation.

Walks Python AST using 3.14's pattern matching and emits FlowByte
instructions. Supports:
- Signal initialization
- DOM element creation (with Div():, Text(), Button())
- Event handlers (on_click)
- Reactive text binding (f-strings)
"""

from __future__ import annotations

import ast

from flow.compiler.evaluator import (
    DynamicStyleSentinel,
    get_style_repr,
    safe_eval_style,
)
from flow.compiler.intrinsics import get_intrinsic_id, is_intrinsic
from flow.compiler.opcodes import OpCode
from flow.compiler.writer import BytecodeWriter


class FlowCompiler(ast.NodeVisitor):
    """
    Python 3.14 AST Visitor for FlowByte compilation.

    Transforms Python syntax into FlowByte instructions.
    """

    def __init__(self) -> None:
        self.writer = BytecodeWriter()
        self.signal_map: dict[str, int] = {}  # Name -> Signal ID
        self.node_id_counter = 0
        self.handler_map: dict[str, str] = {}  # Function name -> label

    def compile(self, source_code: str) -> bytes:
        """Compile Python source to FlowByte binary."""
        tree = ast.parse(source_code)
        self.visit(tree)
        self.writer.emit_op(OpCode.HALT)
        return self.writer.finalize()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handle assignment statements."""
        match node:
            # Signal initialization: count = Signal(0)
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
                    # String signal
                    self.writer.emit_op(OpCode.INIT_SIG_STR)
                    self.writer.emit_u16(sig_id)
                    str_id = self.writer.alloc_string(str(val))
                    self.writer.emit_u16(str_id)

            case _:
                self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions (event handlers)."""
        # Register handler label for later reference
        label = f"handler_{node.name}"
        self.handler_map[node.name] = label

        # Skip compilation of handler body for now
        # It will be emitted when referenced
        pass

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Handle augmented assignment (+=, -=, *=, etc.).

        Stack-based: Load current value, compile operand, apply op, store result.
        Example: count.value += 1 compiles to:
            LOAD_SIG(count), PUSH_NUM(1), ADD_STACK, STORE_SIG(count)
        """
        match node:
            # Signal augmented assignment: sig.value += expr
            case ast.AugAssign(
                target=ast.Attribute(value=ast.Name(id=name), attr="value"),
                op=op,
                value=operand,
            ) if name in self.signal_map:
                sig_id = self.signal_map[name]

                # Load current signal value
                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

                # Compile the operand (pushes to stack)
                self._compile_expr(operand)

                # Emit the operation
                self._emit_binop(op)

                # Store result back to signal
                self.writer.emit_op(OpCode.STORE_SIG)
                self.writer.emit_u16(sig_id)

            case _:
                self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Handle binary operations as expressions.

        This is called when BinOp appears as a statement (rare).
        For expression context, use _compile_expr.
        """
        self._compile_expr(node)
        # Result left on stack - discard if not used
        self.writer.emit_op(OpCode.POP)
        self.writer.emit_u8(1)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Handle comparison operations as statements.

        For expression context, use _compile_expr.
        """
        self._compile_expr(node)
        # Result left on stack - discard if not used
        self.writer.emit_op(OpCode.POP)
        self.writer.emit_u8(1)

    def _compile_expr(self, node: ast.expr) -> None:
        """Compile an expression, leaving result on stack.

        Handles:
        - Constants (PUSH_NUM, PUSH_STR)
        - Signal access (LOAD_SIG)
        - Binary operations (recursive, then op)
        - Comparisons (recursive, then compare op)
        - Function calls (intrinsics)
        """
        match node:
            # Numeric constant
            case ast.Constant(value=val) if isinstance(val, int | float):
                self.writer.emit_op(OpCode.PUSH_NUM)
                self.writer.emit_f64(float(val))

            # String constant
            case ast.Constant(value=val) if isinstance(val, str):
                str_id = self.writer.alloc_string(val)
                self.writer.emit_op(OpCode.PUSH_STR)
                self.writer.emit_u16(str_id)

            # Signal value access: sig.value
            case ast.Attribute(value=ast.Name(id=name), attr="value") if name in self.signal_map:
                sig_id = self.signal_map[name]
                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

            # Binary operation
            case ast.BinOp(left=left, op=op, right=right):
                self._compile_expr(left)
                self._compile_expr(right)
                self._emit_binop(op)

            # Comparison operation
            case ast.Compare(left=left, ops=[op], comparators=[right]):
                self._compile_expr(left)
                self._compile_expr(right)
                self._emit_compare(op)

            # Function call (intrinsics or user functions)
            case ast.Call(func=ast.Name(id=func_name), args=args):
                if is_intrinsic(func_name):
                    self._compile_intrinsic_call(func_name, args)
                else:
                    # TODO: Handle user-defined function calls
                    pass

            # Simple name reference (variable)
            case ast.Name(id=name) if name in self.signal_map:
                # Load signal value
                sig_id = self.signal_map[name]
                self.writer.emit_op(OpCode.LOAD_SIG)
                self.writer.emit_u16(sig_id)

            case _:
                # Unsupported expression type
                pass

    def _emit_binop(self, op: ast.operator) -> None:
        """Emit stack-based binary operation opcode."""
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
                # Unsupported operator
                pass

    def _emit_compare(self, op: ast.cmpop) -> None:
        """Emit stack-based comparison opcode."""
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
                # Unsupported comparison
                pass

    def _compile_intrinsic_call(self, func_name: str, args: list[ast.expr]) -> None:
        """Compile intrinsic function call.

        Pushes all arguments to stack, then emits CALL_INTRINSIC.
        """
        intrinsic_id = get_intrinsic_id(func_name)
        if intrinsic_id is None:
            return

        # Push all arguments to stack (left to right)
        for arg in args:
            self._compile_expr(arg)

        # Emit intrinsic call
        self.writer.emit_op(OpCode.CALL_INTRINSIC)
        self.writer.emit_u8(intrinsic_id)
        self.writer.emit_u8(len(args))

    def visit_With(self, node: ast.With) -> None:
        """Handle with statements (DOM elements)."""
        match node:
            case ast.With(
                items=[
                    ast.withitem(context_expr=ast.Call(func=ast.Name(id=tag), keywords=keywords))
                ],
                body=body,
            ):
                node_id = self.node_id_counter
                self.node_id_counter += 1

                # Emit DOM_CREATE
                tag_str = self.writer.alloc_string(tag.lower())
                self.writer.emit_op(OpCode.DOM_CREATE)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(tag_str)

                # Process keyword arguments (style, class_, id, etc.)
                self._emit_element_attributes(node_id, keywords)

                # Append to root (simplified: always parent 0)
                self.writer.emit_op(OpCode.DOM_APPEND)
                self.writer.emit_u16(0)
                self.writer.emit_u16(node_id)

                # Process children
                for child in body:
                    self.visit(child)

            # Handle with statement without keywords
            case ast.With(
                items=[ast.withitem(context_expr=ast.Call(func=ast.Name(id=tag)))],
                body=body,
            ):
                node_id = self.node_id_counter
                self.node_id_counter += 1

                # Emit DOM_CREATE
                tag_str = self.writer.alloc_string(tag.lower())
                self.writer.emit_op(OpCode.DOM_CREATE)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(tag_str)

                # Append to root (simplified: always parent 0)
                self.writer.emit_op(OpCode.DOM_APPEND)
                self.writer.emit_u16(0)
                self.writer.emit_u16(node_id)

                # Process children
                for child in body:
                    self.visit(child)

            case _:
                self.generic_visit(node)

    def _emit_element_attributes(self, node_id: int, keywords: list[ast.keyword]) -> None:
        """Emit opcodes for element attributes (style, class, id, etc.)."""
        for kw in keywords:
            match kw:
                # class_="..." or cls="..."
                case ast.keyword(arg="class_" | "cls", value=ast.Constant(value=class_val)):
                    class_str = self.writer.alloc_string(str(class_val))
                    self.writer.emit_op(OpCode.DOM_ATTR_CLASS)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(class_str)

                # id="..."
                case ast.keyword(arg="id", value=ast.Constant(value=id_val)):
                    attr_str = self.writer.alloc_string("id")
                    val_str = self.writer.alloc_string(str(id_val))
                    self.writer.emit_op(OpCode.DOM_ATTR)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(attr_str)
                    self.writer.emit_u16(val_str)

                # style=... - use evaluator for static/dynamic detection
                case ast.keyword(arg="style", value=style_node):
                    style_result = safe_eval_style(style_node)
                    if isinstance(style_result, DynamicStyleSentinel):
                        # Dynamic style - emit runtime evaluation
                        self._emit_dynamic_style_evaluated(node_id, style_node)
                    else:
                        # Static style - emit compile-time styles
                        self._emit_static_styles_from_dict(node_id, style_result)

                case _:
                    # Other attributes - generic handling
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
        """Emit opcodes for static style dict like style={"background": "blue"}."""
        for key, value in zip(keys, values, strict=False):
            match (key, value):
                case (ast.Constant(value=prop), ast.Constant(value=val)):
                    # Static property and value
                    prop_str = self.writer.alloc_string(str(prop))
                    val_str = self.writer.alloc_string(str(val))
                    self.writer.emit_op(OpCode.DOM_STYLE_STATIC)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(prop_str)
                    self.writer.emit_u16(val_str)

                case (ast.Constant(value=prop), expr):
                    # Static property, dynamic value - use DOM_STYLE_DYN
                    prop_str = self.writer.alloc_string(str(prop))
                    self._compile_expr(expr)  # Push value to stack
                    self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                    self.writer.emit_u16(node_id)
                    self.writer.emit_u16(prop_str)

                case _:
                    # Skip unsupported patterns
                    pass

    def _emit_style_string(self, node_id: int, style_str: str) -> None:
        """Emit opcodes for style string like style="background: blue; color: red"."""
        # Parse CSS-like style string
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
        """Emit opcodes for statically extracted style dict.

        This is called when safe_eval_style successfully extracts styles.
        Each property is emitted as DOM_STYLE_STATIC.
        """
        for prop, val in style_dict.items():
            prop_str = self.writer.alloc_string(str(prop))
            val_str = self.writer.alloc_string(str(val))
            self.writer.emit_op(OpCode.DOM_STYLE_STATIC)
            self.writer.emit_u16(node_id)
            self.writer.emit_u16(prop_str)
            self.writer.emit_u16(val_str)

    def _emit_dynamic_style_evaluated(self, node_id: int, style_node: ast.expr) -> None:
        """Emit opcodes for dynamic style (when evaluator returns DYNAMIC_STYLE).

        Serializes the AST node as a string for runtime evaluation.
        Emits warning about runtime overhead.
        """
        style_repr = get_style_repr(style_node)
        style_str_id = self.writer.alloc_string(style_repr)

        # Use cssText property for full style replacement
        prop_str = self.writer.alloc_string("cssText")
        self.writer.emit_op(OpCode.PUSH_STR)
        self.writer.emit_u16(style_str_id)
        self.writer.emit_op(OpCode.DOM_STYLE_DYN)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(prop_str)

    def _emit_dynamic_style(self, node_id: int, expr: ast.expr) -> None:
        """Emit opcodes for dynamic style expression (legacy fallback).

        This handles cases where static extraction fails, like:
        - style=get_styles()
        - style=f"background: {color}"
        - style=some_signal.value

        For f-strings, we compile each part and use DOM_STYLE_DYN.
        For other expressions, we compile the whole thing as a dynamic value.
        """
        match expr:
            # f-string: style=f"background: {value}"
            case ast.JoinedStr():
                # Try to extract property name from static prefix
                # This is a simplified handler - real implementation would be more robust
                self._compile_expr(expr)  # Compile f-string to stack
                # Use a generic "style" property (VM will parse it)
                prop_str = self.writer.alloc_string("cssText")
                self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(prop_str)

            case _:
                # Generic expression - compile and apply as cssText
                self._compile_expr(expr)
                prop_str = self.writer.alloc_string("cssText")
                self.writer.emit_op(OpCode.DOM_STYLE_DYN)
                self.writer.emit_u16(node_id)
                self.writer.emit_u16(prop_str)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Handle expression statements (Text, Button calls)."""
        match node.value:
            # Text("hello")
            case ast.Call(
                func=ast.Name(id="Text"),
                args=[ast.Constant(value=text)],
            ):
                self._emit_text_element(str(text))

            # Button("label", on_click=handler)
            case ast.Call(
                func=ast.Name(id="Button"),
                args=[ast.Constant(value=label)],
                keywords=keywords,
            ):
                self._emit_button_element(str(label), keywords)

            # Intrinsic function calls (print, len, str, etc.)
            case ast.Call(func=ast.Name(id=func_name), args=args) if is_intrinsic(func_name):
                self._compile_intrinsic_call(func_name, args)

            case _:
                self.generic_visit(node)

    def _emit_text_element(self, text: str) -> None:
        """Emit opcodes for Text element."""
        node_id = self.node_id_counter
        self.node_id_counter += 1

        # Create span element
        span_str = self.writer.alloc_string("span")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(span_str)

        # Set text content
        text_str = self.writer.alloc_string(text)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(text_str)

        # Append to root
        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)

    def _emit_button_element(self, label: str, keywords: list[ast.keyword]) -> None:
        """Emit opcodes for Button element."""
        node_id = self.node_id_counter
        self.node_id_counter += 1

        # Create button element
        btn_str = self.writer.alloc_string("button")
        self.writer.emit_op(OpCode.DOM_CREATE)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(btn_str)

        # Set label text
        label_str = self.writer.alloc_string(label)
        self.writer.emit_op(OpCode.DOM_TEXT)
        self.writer.emit_u16(node_id)
        self.writer.emit_u16(label_str)

        # Handle on_click
        for kw in keywords:
            if kw.arg == "on_click" and isinstance(kw.value, ast.Name):
                # Emit click listener with placeholder
                self.writer.emit_op(OpCode.DOM_ON_CLICK)
                self.writer.emit_u16(node_id)
                # For now, emit placeholder address
                self.writer.emit_u32(0)  # Will need proper label resolution

        # Append to root
        self.writer.emit_op(OpCode.DOM_APPEND)
        self.writer.emit_u16(0)
        self.writer.emit_u16(node_id)


def compile_to_flowbyte(source: str) -> bytes:
    """Convenience function to compile source to FlowByte binary."""
    compiler = FlowCompiler()
    return compiler.compile(source)
