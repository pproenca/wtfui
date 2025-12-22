import sys
import threading
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from threading import RLock

    from wtfui.tui.renderer.renderer import ConsoleRenderer


class OutputProxy:
    DEBOUNCE_SEC: float = 0.016

    def __init__(
        self,
        original: TextIO,
        renderer: ConsoleRenderer,
        lock: RLock,
    ) -> None:
        self.original = original
        self.renderer = renderer
        self.lock = lock
        self._buffer: list[str] = []
        self._buffer_lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def write(self, data: str) -> int:
        if not data:
            return 0

        with self._buffer_lock:
            self._buffer.append(data)

            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            self._timer = threading.Timer(self.DEBOUNCE_SEC, self._flush_buffer)
            self._timer.daemon = True
            self._timer.start()

        return len(data)

    def _flush_buffer_with_lock(self) -> None:
        if not self._buffer:
            return

        content = "".join(self._buffer)
        self._buffer.clear()

        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        with self.lock:
            self.original.write(self.renderer.get_clear_sequence())

            self.original.write(content)

            if not content.endswith("\n"):
                self.original.write("\n")

            self.original.write(self.renderer.repaint())

            self.original.flush()

    def _flush_buffer(self) -> None:
        with self._buffer_lock:
            self._flush_buffer_with_lock()

    def flush(self) -> None:
        self._flush_buffer()

    def isatty(self) -> bool:
        return self.original.isatty()


class OutputRedirector:
    def __init__(self, renderer: ConsoleRenderer, lock: RLock) -> None:
        self.renderer = renderer
        self.lock = lock
        self._orig_stdout: TextIO | None = None
        self._orig_stderr: TextIO | None = None

    def __enter__(self) -> None:
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        self._stdout_proxy = OutputProxy(self._orig_stdout, self.renderer, self.lock)
        self._stderr_proxy = OutputProxy(self._orig_stderr, self.renderer, self.lock)
        sys.stdout = self._stdout_proxy
        sys.stderr = self._stderr_proxy

    def __exit__(self, *args: Any) -> None:
        if hasattr(self, "_stdout_proxy"):
            self._stdout_proxy.flush()
        if hasattr(self, "_stderr_proxy"):
            self._stderr_proxy.flush()

        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout
        if self._orig_stderr is not None:
            sys.stderr = self._orig_stderr
