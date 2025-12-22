from wtfui.core._greenlet_guard import check_greenlet_contamination as _check_greenlet

_check_greenlet()
del _check_greenlet

from wtfui.core.component import component  # noqa: E402
from wtfui.core.computed import Computed  # noqa: E402
from wtfui.core.effect import Effect  # noqa: E402
from wtfui.core.element import Element  # noqa: E402
from wtfui.core.injection import get_provider, provide  # noqa: E402
from wtfui.core.signal import Signal  # noqa: E402
from wtfui.web.rpc import rpc  # noqa: E402

__all__ = [
    "Computed",
    "Effect",
    "Element",
    "Signal",
    "component",
    "get_provider",
    "provide",
    "rpc",
]

__version__ = "0.1.0"
