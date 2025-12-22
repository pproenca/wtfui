import ast
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from wtfui.web.compiler.writer import MAGIC_HEADER, BytecodeWriter
from wtfui.web.compiler.wtfuibyte import WtfUICompiler


@dataclass(frozen=True)
class CompilationUnit:
    node_id: int
    bytecode: bytes
    strings: tuple[str, ...]
    children: tuple[int, ...]
    css_classes: tuple[tuple[str, dict[str, str]], ...] = ()


@dataclass
class ParallelCompiler:
    max_workers: int = 4
    _results: dict[int, CompilationUnit] = field(default_factory=dict)
    _next_id: int = field(default=0)
    _id_lock: threading.Lock = field(default_factory=threading.Lock)

    def compile(self, source: str) -> bytes:
        tree = ast.parse(source)

        units = self._extract_units(tree)

        if len(units) <= 1:
            compiler = WtfUICompiler()
            binary, _css_output = compiler.compile_with_css(source)

            self._results[0] = CompilationUnit(
                node_id=0,
                bytecode=binary,
                strings=tuple(compiler.writer._strings),
                children=(),
                css_classes=tuple(
                    (name, dict(style)) for name, style in compiler.css_gen._styles.items()
                ),
            )
            return binary

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._compile_unit, unit): unit_id
                for unit_id, unit in enumerate(units)
            }

            for future in as_completed(futures):
                unit_id = futures[future]
                result = future.result()
                self._results[unit_id] = result

        return self._merge_results()

    def _extract_units(self, tree: ast.Module) -> list[ast.AST]:
        units: list[ast.AST] = []

        for node in ast.walk(tree):
            match node:
                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    units.append(node)
                case ast.With():
                    units.append(node)

        if not units:
            units = [tree]

        return units

    def _compile_unit(self, node: ast.AST) -> CompilationUnit:
        from wtfui.web.compiler.css import CSSGenerator

        writer = BytecodeWriter()
        node_id = self._allocate_id()
        css_gen = CSSGenerator(prefix="fl")

        css_classes: list[tuple[str, dict[str, str]]] = []

        if isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    for keyword in item.context_expr.keywords:
                        if keyword.arg == "style" and isinstance(keyword.value, ast.Dict):
                            style_dict = {}
                            for k, v in zip(keyword.value.keys, keyword.value.values, strict=True):
                                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                                    style_dict[str(k.value)] = str(v.value)
                            if style_dict:
                                class_name = css_gen.register(style_dict)
                                css_classes.append((class_name, style_dict))

        match node:
            case ast.Module(body=body):
                compiler = WtfUICompiler()
                compiler.writer = writer
                for stmt in body:
                    compiler.visit(stmt)

            case ast.FunctionDef() | ast.AsyncFunctionDef():
                compiler = WtfUICompiler()
                compiler.writer = writer
                compiler.visit(node)

            case ast.With():
                compiler = WtfUICompiler()
                compiler.writer = writer
                compiler.visit(node)

            case _:
                compiler = WtfUICompiler()
                compiler.writer = writer
                compiler.visit(node)

        bytecode = bytes(writer.code)
        strings = tuple(writer._strings)
        children: tuple[int, ...] = ()

        return CompilationUnit(
            node_id=node_id,
            bytecode=bytecode,
            strings=strings,
            children=children,
            css_classes=tuple(css_classes),
        )

    def _allocate_id(self) -> int:
        with self._id_lock:
            current = self._next_id
            self._next_id = current + 1
            return current

    def get_merged_css(self) -> str:
        style_to_class: dict[tuple[tuple[str, str], ...], str] = {}
        all_styles: list[tuple[str, dict[str, str]]] = []

        for result in self._results.values():
            for _class_name, style_dict in result.css_classes:
                style_key = tuple(sorted(style_dict.items()))

                if style_key not in style_to_class:
                    canonical_name = f"fl-{len(style_to_class):04x}"
                    style_to_class[style_key] = canonical_name
                    all_styles.append((canonical_name, style_dict))

        css_lines = []
        for class_name, style_dict in all_styles:
            props = "; ".join(f"{k}: {v}" for k, v in style_dict.items())
            css_lines.append(f".{class_name} {{ {props}; }}")

        return "\n".join(css_lines)

    def _merge_results(self) -> bytes:
        string_map: dict[str, int] = {}
        all_strings: list[str] = []

        for result in self._results.values():
            for s in result.strings:
                if s not in string_map:
                    string_map[s] = len(all_strings)
                    all_strings.append(s)

        merged_code = bytearray()
        for result in sorted(self._results.values(), key=lambda r: r.node_id):
            merged_code.extend(result.bytecode)

        merged_code.append(0xFF)

        writer = BytecodeWriter()
        for s in all_strings:
            writer.alloc_string(s)

        import struct

        str_section = bytearray()
        str_section.extend(struct.pack("!H", len(all_strings)))
        for s in all_strings:
            encoded = s.encode("utf-8")
            str_section.extend(struct.pack("!H", len(encoded)))
            str_section.extend(encoded)

        return MAGIC_HEADER + bytes(str_section) + bytes(merged_code)


def compile_parallel(source: str, max_workers: int = 4) -> bytes:
    compiler = ParallelCompiler(max_workers=max_workers)
    return compiler.compile(source)


@dataclass(frozen=True)
class ShardedStringPool:
    shards: tuple[tuple[str, ...], ...]

    @classmethod
    def create(cls, num_shards: int) -> ShardedStringPool:
        return cls(shards=tuple(() for _ in range(num_shards)))

    def add_to_shard(self, shard_id: int, string: str) -> ShardedStringPool:
        new_shards = list(self.shards)
        new_shards[shard_id] = (*self.shards[shard_id], string)
        return ShardedStringPool(shards=tuple(new_shards))

    def merge(self) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for shard in self.shards:
            for s in shard:
                if s not in seen:
                    seen.add(s)
                    result.append(s)
        return tuple(result)
