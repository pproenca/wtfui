__all__ = ["ConsoleRenderer", "LayoutAdapter", "ReactiveLayoutAdapter", "RenderTreeBuilder"]


def __getattr__(name: str):
    if name == "ConsoleRenderer":
        from wtfui.tui.renderer import ConsoleRenderer

        return ConsoleRenderer
    if name == "LayoutAdapter":
        from wtfui.tui.adapter import LayoutAdapter

        return LayoutAdapter
    if name == "ReactiveLayoutAdapter":
        from wtfui.tui.adapter import ReactiveLayoutAdapter

        return ReactiveLayoutAdapter
    if name == "RenderTreeBuilder":
        from wtfui.tui.builder import RenderTreeBuilder

        return RenderTreeBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
