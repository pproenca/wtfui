"""Tests for tree shaking call graph analysis."""

from wtfui.web.compiler.shaker import CallGraph


class TestCallGraphBuilder:
    """Test call graph construction from AST."""

    def test_simple_function_call(self) -> None:
        """Detects direct function calls."""
        source = """
def helper():
    pass

def main():
    helper()
"""
        graph = CallGraph.from_source(source)
        assert "helper" in graph.calls_from("main")

    def test_no_calls_empty_set(self) -> None:
        """Function with no calls has empty call set."""
        source = """
def standalone():
    x = 1 + 2
"""
        graph = CallGraph.from_source(source)
        assert graph.calls_from("standalone") == set()

    def test_nested_calls(self) -> None:
        """Detects calls inside function call args."""
        source = """
def a(): pass
def b(): pass

def main():
    print(a(), b())
"""
        graph = CallGraph.from_source(source)
        calls = graph.calls_from("main")
        assert "a" in calls
        assert "b" in calls

    def test_method_calls_excluded(self) -> None:
        """Method calls (obj.method()) are not tracked as globals."""
        source = """
def main():
    obj.method()
    other_func()
"""
        graph = CallGraph.from_source(source)
        calls = graph.calls_from("main")
        assert "method" not in calls
        assert "other_func" in calls


class TestReachabilityAnalysis:
    """Test dead code detection via reachability."""

    def test_reachable_from_entry(self) -> None:
        """Functions reachable from entry are marked used."""
        source = """
def helper():
    pass

def unused():
    pass

def App():
    helper()
"""
        graph = CallGraph.from_source(source)
        reachable = graph.reachable_from("App")

        assert "App" in reachable
        assert "helper" in reachable
        assert "unused" not in reachable

    def test_transitive_reachability(self) -> None:
        """Transitive calls are included."""
        source = """
def level3():
    pass

def level2():
    level3()

def level1():
    level2()

def App():
    level1()
"""
        graph = CallGraph.from_source(source)
        reachable = graph.reachable_from("App")

        assert "level1" in reachable
        assert "level2" in reachable
        assert "level3" in reachable

    def test_cycle_handling(self) -> None:
        """Cyclic calls don't cause infinite loop."""
        source = """
def a():
    b()

def b():
    a()

def App():
    a()
"""
        graph = CallGraph.from_source(source)
        reachable = graph.reachable_from("App")

        assert "a" in reachable
        assert "b" in reachable


class TestDynamicUsageDetection:
    """Test detection of dynamic dispatch that breaks tree shaking."""

    def test_detects_getattr_dynamic_call(self) -> None:
        """getattr(obj, name) is flagged as dynamic."""
        source = """
def dangerous():
    func = getattr(module, func_name)
    func()
"""
        graph = CallGraph.from_source(source)
        assert graph.has_dynamic_dispatch("dangerous")

    def test_detects_globals_access(self) -> None:
        """globals()[name] is flagged as dynamic."""
        source = """
def dangerous():
    globals()["func"]()
"""
        graph = CallGraph.from_source(source)
        assert graph.has_dynamic_dispatch("dangerous")

    def test_normal_function_not_flagged(self) -> None:
        """Normal static calls are not flagged."""
        source = """
def safe():
    helper()
"""
        graph = CallGraph.from_source(source)
        assert not graph.has_dynamic_dispatch("safe")

    def test_any_dynamic_in_module(self) -> None:
        """Check if any function has dynamic dispatch."""
        source = """
def safe():
    helper()

def dangerous():
    getattr(mod, name)()
"""
        graph = CallGraph.from_source(source)
        assert graph.has_any_dynamic_dispatch() is True
