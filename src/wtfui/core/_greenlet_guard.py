import os
import warnings


class GreenletContaminationError(Exception):
    pass


class GreenletContaminationWarning(UserWarning):
    pass


def check_greenlet_contamination() -> None:
    try:
        import greenlet  # noqa: F401
    except ImportError:
        return

    message = (
        "greenlet detected - GIL may be re-enabled!\n"
        "\n"
        "Fuse performs best with Python 3.14t (free-threaded) WITHOUT greenlet.\n"
        "greenlet forces the GIL back on, defeating No-GIL parallelism.\n"
        "\n"
        "This usually happens when:\n"
        "  - Running with `--extra e2e` (installs playwright -> greenlet)\n"
        "  - A dependency transitively imports greenlet (SQLAlchemy, gevent)\n"
        "\n"
        "To fix:\n"
        "  1. Use: uv sync --extra dev --extra demo\n"
        "  2. Run E2E tests in a separate virtualenv\n"
        "  3. See docs/adr/0001-reject-greenlet.md for details\n"
        "\n"
        "Set WTFUI_GREENLET_ERROR=1 to make this a fatal error."
    )

    if os.environ.get("WTFUI_GREENLET_ERROR") == "1":
        raise GreenletContaminationError(message)

    warnings.warn(message, GreenletContaminationWarning, stacklevel=2)
