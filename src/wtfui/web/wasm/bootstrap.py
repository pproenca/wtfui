import sys
from typing import TYPE_CHECKING, Any

from wtfui.core.registry import ElementRegistry
from wtfui.web.renderer import DOMRenderer
from wtfui.web.wasm.platform import is_browser

if TYPE_CHECKING:
    from wtfui.core.element import Element


def get_pyodide() -> Any:
    return sys.modules.get("pyodide")


def get_document() -> Any:
    if not is_browser():
        return None

    js = sys.modules.get("js")
    if js is not None:
        return getattr(js, "document", None)

    return None


def _get_proxy_factory() -> Any:
    pyodide = get_pyodide()
    if pyodide is None:
        return lambda x: x

    ffi = getattr(pyodide, "ffi", None)
    if ffi is not None:
        return getattr(ffi, "create_proxy", lambda x: x)

    return lambda x: x


class WtfUIApp:
    def __init__(self, root: Element) -> None:
        self.root = root
        self._registry = ElementRegistry()
        self._registry.register_tree(root)
        self._renderer: DOMRenderer | None = None

    def mount(
        self,
        document: Any | None = None,
        container_id: str = "wtfui-root",
    ) -> None:
        if document is None:
            document = get_document()

        if document is None:
            msg = "Cannot mount: not in browser environment"
            raise RuntimeError(msg)

        proxy_factory = _get_proxy_factory()
        self._renderer = DOMRenderer(document, proxy_factory)

        dom_tree = self._renderer.render(self.root)

        container = document.getElementById(container_id)
        if container is not None:
            container.innerHTML = ""
            container.appendChild(dom_tree)


def mount(
    root: Element,
    document: Any | None = None,
    container_id: str = "wtfui-root",
) -> WtfUIApp:
    app = WtfUIApp(root)
    app.mount(document, container_id)
    return app
