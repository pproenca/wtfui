# tests/compiler/test_optimizer.py
"""Tests for WtfUIByte optimizer - constant folding and dead code elimination."""

import ast

from wtfui.web.compiler.opcodes import OpCode


class TestConstantFolding:
    """Tests for compile-time constant expression evaluation."""

    def test_folds_numeric_addition(self) -> None:
        """Constant numeric addition is evaluated at compile time."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 2 + 3")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        # Should become: x = 5
        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 5

    def test_folds_numeric_subtraction(self) -> None:
        """Constant numeric subtraction is evaluated at compile time."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 10 - 4")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 6

    def test_folds_numeric_multiplication(self) -> None:
        """Constant numeric multiplication is evaluated at compile time."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 3 * 7")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 21

    def test_folds_numeric_division(self) -> None:
        """Constant numeric division is evaluated at compile time."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 20 / 4")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 5.0

    def test_folds_nested_expressions(self) -> None:
        """Nested constant expressions are fully folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = (2 + 3) * 4")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 20

    def test_folds_string_concatenation(self) -> None:
        """Constant string concatenation is evaluated at compile time."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 'hello' + ' ' + 'world'")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == "hello world"

    def test_preserves_non_constant_expressions(self) -> None:
        """Expressions with variables are not folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = a + 3")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        # Should remain: x = a + 3 (BinOp, not Constant)
        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.BinOp)

    def test_folds_comparison_true(self) -> None:
        """Constant comparison evaluating to True is folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 5 > 3")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value is True

    def test_folds_comparison_false(self) -> None:
        """Constant comparison evaluating to False is folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = 2 > 10")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value is False

    def test_folds_unary_negation(self) -> None:
        """Unary negation of constant is folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = -5")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == -5

    def test_folds_unary_not(self) -> None:
        """Unary not of constant is folded."""
        from wtfui.web.compiler.optimizer import ConstantFolder

        tree = ast.parse("x = not True")
        folder = ConstantFolder()
        optimized = folder.visit(tree)
        assert isinstance(optimized, ast.Module)

        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value is False


class TestDeadCodeElimination:
    """Tests for removing unreachable or unused code."""

    def test_removes_if_false_branch(self) -> None:
        """Code in 'if False' block is eliminated."""
        from wtfui.web.compiler.optimizer import DeadCodeEliminator

        tree = ast.parse("""
if False:
    x = 1
else:
    x = 2
""")
        eliminator = DeadCodeEliminator()
        optimized = eliminator.visit(tree)
        ast.fix_missing_locations(optimized)
        assert isinstance(optimized, ast.Module)

        # Should become just: x = 2
        assert len(optimized.body) == 1
        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 2

    def test_preserves_if_true_branch(self) -> None:
        """Code in 'if True' block is kept, else is eliminated."""
        from wtfui.web.compiler.optimizer import DeadCodeEliminator

        tree = ast.parse("""
if True:
    x = 1
else:
    x = 2
""")
        eliminator = DeadCodeEliminator()
        optimized = eliminator.visit(tree)
        ast.fix_missing_locations(optimized)
        assert isinstance(optimized, ast.Module)

        # Should become just: x = 1
        assert len(optimized.body) == 1
        assign = optimized.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.Constant)
        assert assign.value.value == 1

    def test_preserves_dynamic_if(self) -> None:
        """If statements with non-constant conditions are preserved."""
        from wtfui.web.compiler.optimizer import DeadCodeEliminator

        tree = ast.parse("""
if some_var:
    x = 1
else:
    x = 2
""")
        eliminator = DeadCodeEliminator()
        optimized = eliminator.visit(tree)
        assert isinstance(optimized, ast.Module)

        # Should remain as If statement
        assert len(optimized.body) == 1
        assert isinstance(optimized.body[0], ast.If)

    def test_removes_pass_statements(self) -> None:
        """Redundant pass statements are removed."""
        from wtfui.web.compiler.optimizer import DeadCodeEliminator

        tree = ast.parse("""
x = 1
pass
y = 2
pass
""")
        eliminator = DeadCodeEliminator()
        optimized = eliminator.visit(tree)
        assert isinstance(optimized, ast.Module)

        # Should have only the assignments
        assert len(optimized.body) == 2
        assert all(isinstance(stmt, ast.Assign) for stmt in optimized.body)

    def test_keeps_pass_in_empty_block(self) -> None:
        """Pass statement is kept when it's the only statement in a block."""
        from wtfui.web.compiler.optimizer import DeadCodeEliminator

        tree = ast.parse("""
def empty_func():
    pass
""")
        eliminator = DeadCodeEliminator()
        optimized = eliminator.visit(tree)
        assert isinstance(optimized, ast.Module)

        # Function body should still have pass
        func = optimized.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert len(func.body) == 1
        assert isinstance(func.body[0], ast.Pass)


class TestOptimizePipeline:
    """Tests for the complete optimization pipeline."""

    def test_optimize_combines_passes(self) -> None:
        """optimize() applies both constant folding and dead code elimination."""
        from wtfui.web.compiler.optimizer import optimize

        tree = ast.parse("""
x = 2 + 3
if False:
    y = 10
else:
    y = x
""")
        optimized = optimize(tree)
        assert isinstance(optimized, ast.Module)

        # Should have: x = 5 and y = x
        assert len(optimized.body) == 2

        # First: x = 5 (constant folded)
        assign_x = optimized.body[0]
        assert isinstance(assign_x, ast.Assign)
        assert isinstance(assign_x.value, ast.Constant)
        assert assign_x.value.value == 5

        # Second: y = x (dead code eliminated the if False branch)
        assign_y = optimized.body[1]
        assert isinstance(assign_y, ast.Assign)

    def test_optimize_idempotent(self) -> None:
        """Running optimize twice produces same result."""
        from wtfui.web.compiler.optimizer import optimize

        tree = ast.parse("x = 2 + 3 * 4")
        optimized1 = optimize(tree)
        optimized2 = optimize(optimized1)
        assert isinstance(optimized1, ast.Module)
        assert isinstance(optimized2, ast.Module)

        # Both should produce x = 14
        assign1 = optimized1.body[0]
        assign2 = optimized2.body[0]
        assert isinstance(assign1, ast.Assign)
        assert isinstance(assign2, ast.Assign)
        assert isinstance(assign1.value, ast.Constant)
        assert isinstance(assign2.value, ast.Constant)
        assert assign1.value.value == 14
        assert assign2.value.value == 14

    def test_optimize_preserves_semantics(self) -> None:
        """Optimization preserves program semantics."""
        from wtfui.web.compiler.optimizer import optimize

        # Signal initialization should be preserved
        tree = ast.parse("""
count = Signal(0)
with Div(class_="container"):
    Text("Hello")
""")
        optimized = optimize(tree)
        assert isinstance(optimized, ast.Module)

        # Should have same structure
        assert len(optimized.body) == 2


class TestOptimizeWtfUIByteIntegration:
    """Integration tests with WtfUIByte compiler."""

    def test_optimized_compilation_produces_valid_bytecode(self) -> None:
        """Optimized AST compiles to valid WtfUIByte."""
        from wtfui.web.compiler.optimizer import optimize
        from wtfui.web.compiler.writer import MAGIC_HEADER
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        tree = ast.parse("""
count = Signal(2 + 3)
with Div(class_="test"):
    Text("Hello")
""")
        optimized = optimize(tree)

        compiler = WtfUICompiler()
        compiler.visit(optimized)
        compiler.writer.emit_op(OpCode.HALT)
        bytecode = compiler.writer.finalize()

        assert bytecode.startswith(MAGIC_HEADER)
        assert bytecode.endswith(b"\xff")

    def test_optimized_compilation_smaller_output(self) -> None:
        """Optimized code produces equal or smaller bytecode."""
        from wtfui.web.compiler.optimizer import optimize
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler, compile_to_wtfuibyte

        source = """
x = 2 + 3
if False:
    y = 100
else:
    y = 1
"""
        # Unoptimized
        unopt_bytecode = compile_to_wtfuibyte(source)

        # Optimized
        tree = ast.parse(source)
        optimized = optimize(tree)

        compiler = WtfUICompiler()
        compiler.visit(optimized)
        compiler.writer.emit_op(OpCode.HALT)
        opt_bytecode = compiler.writer.finalize()

        # Optimized should not be larger
        assert len(opt_bytecode) <= len(unopt_bytecode)
