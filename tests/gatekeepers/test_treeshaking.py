"""Gatekeeper: Tree shaking effectiveness and safety."""

import pytest

from wtfui.web.compiler.linker import filter_unreachable
from wtfui.web.compiler.shaker import CallGraph


@pytest.mark.gatekeeper
class TestTreeShakingGatekeeper:
    """Verify tree shaking correctly eliminates dead code."""

    def test_reduces_function_count(self) -> None:
        """Tree shaking should reduce function count significantly."""
        # Simulate a module with many unused functions
        source = "\n".join(
            [
                "def App(): helper1()",
                "def helper1(): helper2()",
                "def helper2(): pass",
            ]
            + [f"def unused{i}(): pass" for i in range(50)]
        )

        graph = CallGraph.from_source(source)
        all_funcs = {"App", "helper1", "helper2"} | {f"unused{i}" for i in range(50)}

        kept = filter_unreachable(all_funcs, graph, entry="App")

        # Should keep only App, helper1, helper2
        assert len(kept) == 3
        elimination_rate = 1 - len(kept) / len(all_funcs)
        assert elimination_rate > 0.9, f"Only {elimination_rate:.0%} eliminated"

        print(
            f"\n[Tree Shaking] Eliminated {len(all_funcs) - len(kept)}/{len(all_funcs)} functions"
        )
        print(f"[Tree Shaking] {elimination_rate:.1%} dead code removed")

    def test_preserves_all_transitive_deps(self) -> None:
        """Tree shaking must preserve entire call chain."""
        source = """
def level5(): pass
def level4(): level5()
def level3(): level4()
def level2(): level3()
def level1(): level2()
def App(): level1()
def unused(): pass
"""
        graph = CallGraph.from_source(source)
        all_funcs = {"App", "level1", "level2", "level3", "level4", "level5", "unused"}

        kept = filter_unreachable(all_funcs, graph, entry="App")

        # Must preserve entire chain
        for level in ["App", "level1", "level2", "level3", "level4", "level5"]:
            assert level in kept, f"Missing transitive dep: {level}"
        assert "unused" not in kept

    def test_handles_large_codebase(self) -> None:
        """Tree shaking scales to large codebases."""
        # Generate 1000 functions, 100 reachable
        funcs = []
        funcs.append("def App(): f0()")
        for i in range(100):
            funcs.append(f"def f{i}(): f{i + 1}() if {i} < 99 else None")
        for i in range(100, 1000):
            funcs.append(f"def unused{i}(): pass")

        source = "\n".join(funcs)
        graph = CallGraph.from_source(source)

        all_funcs = (
            {"App"} | {f"f{i}" for i in range(100)} | {f"unused{i}" for i in range(100, 1000)}
        )

        import time

        start = time.perf_counter()
        filter_unreachable(all_funcs, graph, entry="App")
        elapsed = time.perf_counter() - start

        # Should complete in < 100ms for 1000 functions
        assert elapsed < 0.1, f"Tree shaking too slow: {elapsed:.3f}s"
        print(f"\n[Tree Shaking] Analyzed 1000 functions in {elapsed * 1000:.1f}ms")
