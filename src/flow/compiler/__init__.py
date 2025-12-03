"""Flow Compiler - AST transformation and bytecode generation."""

from flow.compiler.analyzer import ModuleType, SplitBrainAnalyzer
from flow.compiler.cache import ArtifactCache, CacheEntry
from flow.compiler.css import CSSGenerator
from flow.compiler.evaluator import (
    DYNAMIC_STYLE,
    DynamicStyleSentinel,
    get_style_repr,
    is_static_style,
    safe_eval_style,
)
from flow.compiler.flowbyte import FlowCompiler, compile_to_flowbyte
from flow.compiler.graph import DependencyGraph, DependencyNode
from flow.compiler.importer import (
    FlowImportHook,
    get_debug_output_dir,
    install_import_hook,
    set_debug_mode,
    uninstall_import_hook,
)
from flow.compiler.intrinsics import IntrinsicID, get_intrinsic_id, is_intrinsic
from flow.compiler.linker import FunctionRef, Linker, LinkResult
from flow.compiler.opcodes import OpCode
from flow.compiler.parallel import (
    CompilationUnit,
    ParallelCompiler,
    ShardedStringPool,
    compile_parallel,
)
from flow.compiler.transformer import (
    ClientSafeTransformer,
    compile_for_client,
    transform_for_client,
)
from flow.compiler.validator import (
    BoundarySentinel,
    BoundarySentinelError,
    SecurityViolation,
)
from flow.compiler.writer import MAGIC_HEADER, BytecodeWriter

__all__ = [
    # Style Evaluator
    "DYNAMIC_STYLE",
    # Compiler
    "MAGIC_HEADER",
    # Cache
    "ArtifactCache",
    # Security
    "BoundarySentinel",
    "BoundarySentinelError",
    "BytecodeWriter",
    # CSS Generator
    "CSSGenerator",
    "CacheEntry",
    "ClientSafeTransformer",
    "CompilationUnit",
    # Graph & Analysis
    "DependencyGraph",
    "DependencyNode",
    "DynamicStyleSentinel",
    "FlowCompiler",
    "FlowImportHook",
    "FunctionRef",
    "IntrinsicID",
    "LinkResult",
    # Linker
    "Linker",
    "ModuleType",
    "OpCode",
    "ParallelCompiler",
    "SecurityViolation",
    "ShardedStringPool",
    "SplitBrainAnalyzer",
    "compile_for_client",
    "compile_parallel",
    "compile_to_flowbyte",
    "get_debug_output_dir",
    "get_intrinsic_id",
    "get_style_repr",
    "install_import_hook",
    "is_intrinsic",
    "is_static_style",
    "safe_eval_style",
    "set_debug_mode",
    "transform_for_client",
    "uninstall_import_hook",
]
