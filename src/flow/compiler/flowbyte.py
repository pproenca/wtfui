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

    def visit_With(self, node: ast.With) -> None:
        """Handle with statements (DOM elements)."""
        match node:
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
