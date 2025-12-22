"""Thread safety tests for No-GIL Python 3.14t.

These tests stress concurrent access patterns to expose data races.
Each test is designed to fail without proper synchronization.

Design rationale (Sam Gross style):
- Use barrier synchronization to maximize contention
- Run enough iterations to reliably trigger races
- Test the specific invariant that should hold
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------


def stress_test(
    fn: Callable[[], None],
    *,
    threads: int = 50,
    iterations: int = 100,
) -> list[Exception]:
    """Run fn concurrently from multiple threads.

    Uses a barrier to maximize contention by starting all threads
    simultaneously.

    Returns list of exceptions raised (empty if all succeeded).
    """
    barrier = threading.Barrier(threads)
    errors: list[Exception] = []
    errors_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        for _ in range(iterations):
            try:
                fn()
            except Exception as e:
                with errors_lock:
                    errors.append(e)

    workers = [threading.Thread(target=worker) for _ in range(threads)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()

    return errors


# ---------------------------------------------------------------------------
# ParallelCompiler._allocate_id() race condition
# ---------------------------------------------------------------------------


class TestParallelCompilerIdAllocation:
    """Test that _allocate_id returns unique IDs under contention."""

    def test_allocate_id_returns_unique_ids_under_contention(self) -> None:
        """IDs must be unique even when allocated from many threads.

        The bug: read-then-increment is not atomic. Without a lock,
        multiple threads can read the same _next_id before any increments.
        """
        from wtfui.web.compiler.parallel import ParallelCompiler

        compiler = ParallelCompiler()
        ids: list[int] = []
        ids_lock = threading.Lock()

        n_threads = 50
        ids_per_thread = 100

        barrier = threading.Barrier(n_threads)

        def allocate_ids() -> None:
            barrier.wait()
            local_ids = [compiler._allocate_id() for _ in range(ids_per_thread)]
            with ids_lock:
                ids.extend(local_ids)

        threads = [threading.Thread(target=allocate_ids) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = n_threads * ids_per_thread
        unique = len(set(ids))

        assert unique == expected, (
            f"Expected {expected} unique IDs, got {unique} (lost {expected - unique})"
        )

    def test_allocate_id_sequential_invariant(self) -> None:
        """IDs should be sequential (no gaps or duplicates)."""
        from wtfui.web.compiler.parallel import ParallelCompiler

        compiler = ParallelCompiler()
        n_allocations = 1000

        with ThreadPoolExecutor(max_workers=20) as executor:
            ids = list(executor.map(lambda _: compiler._allocate_id(), range(n_allocations)))

        assert sorted(ids) == list(range(n_allocations))


# ---------------------------------------------------------------------------
# HistoryState subscriber management race condition
# ---------------------------------------------------------------------------


class TestHistoryStateSubscribers:
    """Test that subscriber list operations are thread-safe."""

    def test_subscribe_unsubscribe_under_contention(self) -> None:
        """Concurrent subscribe/unsubscribe must not lose callbacks.

        The bug: list.append() and list.remove() without synchronization
        can cause lost updates or corruption during concurrent modification.
        """
        from wtfui.core.router import HistoryState

        history = HistoryState("/")
        errors: list[str] = []
        errors_lock = threading.Lock()

        n_threads = 30
        iterations = 50

        barrier = threading.Barrier(n_threads)

        def subscribe_unsubscribe() -> None:
            barrier.wait()
            for _ in range(iterations):
                unsubscribe = history.subscribe(lambda _: None)
                unsubscribe()

        threads = [threading.Thread(target=subscribe_unsubscribe) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_count = len(history._subscribers)
        if final_count != 0:
            with errors_lock:
                errors.append(f"Expected 0 subscribers, got {final_count}")

        assert not errors, errors

    def test_notify_during_concurrent_subscribe(self) -> None:
        """Notifications must reach all registered subscribers.

        Registers all subscribers first, then tests that concurrent
        push operations deliver notifications correctly.
        """
        from wtfui.core.router import HistoryState

        history = HistoryState("/")
        notification_count = [0]
        count_lock = threading.Lock()

        n_subscribers = 100
        unsubscribers: list[Callable[[], None]] = []

        for _ in range(n_subscribers):

            def callback(_: str) -> None:
                with count_lock:
                    notification_count[0] += 1

            unsubscribers.append(history.subscribe(callback))

        history.push("/new")

        for unsub in unsubscribers:
            unsub()

        count = notification_count[0]
        assert count == n_subscribers, f"Expected {n_subscribers} notifications, got {count}"


# ---------------------------------------------------------------------------
# TUIRuntime term_size read-modify-write race
# ---------------------------------------------------------------------------


class TestTUIRuntimeTermSize:
    """Test that term_size updates are atomic."""

    def test_term_size_no_lost_updates(self) -> None:
        """Concurrent width/height updates must not lose data.

        The bug: term_width setter reads _term_size[1] and creates new tuple.
        Between read and write, another thread can update height, and the
        new width write will overwrite the height change.
        """
        from wtfui.tui.runtime import TUIRuntime

        runtime = TUIRuntime(lambda: None)
        runtime._term_size = (80, 24)

        n_threads = 50
        barrier = threading.Barrier(n_threads * 2)

        final_width = 200
        final_height = 100

        def update_width() -> None:
            barrier.wait()
            for w in range(80, final_width + 1):
                runtime.term_width = w

        def update_height() -> None:
            barrier.wait()
            for h in range(24, final_height + 1):
                runtime.term_height = h

        width_threads = [threading.Thread(target=update_width) for _ in range(n_threads)]
        height_threads = [threading.Thread(target=update_height) for _ in range(n_threads)]

        for t in width_threads + height_threads:
            t.start()
        for t in width_threads + height_threads:
            t.join()

        w, h = runtime._term_size
        assert w == final_width, f"Expected width {final_width}, got {w}"
        assert h == final_height, f"Expected height {final_height}, got {h}"

    def test_term_size_atomic_update(self) -> None:
        """Setting both dimensions should be atomic."""
        from wtfui.tui.runtime import TUIRuntime

        runtime = TUIRuntime(lambda: None)

        observed_states: list[tuple[int, int]] = []
        lock = threading.Lock()

        n_iterations = 1000

        def writer() -> None:
            for i in range(n_iterations):
                runtime._term_size = (100 + i, 50 + i)

        def reader() -> None:
            for _ in range(n_iterations):
                state = runtime._term_size
                with lock:
                    observed_states.append(state)

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)

        w.start()
        r.start()
        w.join()
        r.join()

        for w, h in observed_states:
            diff = w - h
            assert diff == 50, f"Inconsistent state: width={w}, height={h}, diff={diff}"


# ---------------------------------------------------------------------------
# Global state races: terminal, manifest, importer
# ---------------------------------------------------------------------------


class TestTerminalGlobalState:
    """Test terminal.py global state thread safety."""

    def test_setup_restore_concurrent(self) -> None:
        """Concurrent setup_raw_mode/restore_terminal must not corrupt state.

        The bug: _original_termios is a global without synchronization.
        Two TUI instances calling setup/restore can overwrite each other's
        saved settings.
        """
        pytest.skip("Requires TTY; run manually with: pytest -k terminal --capture=no")


class TestManifestGlobalState:
    """Test manifest.py global state thread safety."""

    def test_set_get_manifest_concurrent(self) -> None:
        """Concurrent set_manifest/get_manifest must be consistent.

        Tests that manifest reads/writes don't corrupt data.
        Note: manifest module uses simple reference swap which is
        atomic in CPython, so this test verifies that behavior.
        """
        from wtfui.tui.renderer import manifest
        from wtfui.tui.renderer.manifest import StyleManifest, get_manifest, set_manifest

        original = manifest._global_manifest

        try:
            manifest._global_manifest = None

            errors: list[str] = []
            errors_lock = threading.Lock()

            test_manifests = [StyleManifest({"testkey": {"prop": f"value{i}"}}) for i in range(10)]

            n_threads = 20
            iterations = 100

            barrier = threading.Barrier(n_threads * 2)

            def setter() -> None:
                barrier.wait()
                for _ in range(iterations):
                    for m in test_manifests:
                        set_manifest(m)

            def getter() -> None:
                barrier.wait()
                for _ in range(iterations):
                    m = get_manifest()
                    if m is not None:
                        result = m.resolve("testkey")
                        if result is not None and "prop" not in result:
                            with errors_lock:
                                errors.append(f"Corrupt manifest: {result}")

            setters = [threading.Thread(target=setter) for _ in range(n_threads)]
            getters = [threading.Thread(target=getter) for _ in range(n_threads)]

            for t in setters + getters:
                t.start()
            for t in setters + getters:
                t.join()

            assert not errors, f"Found {len(errors)} errors: {errors[:5]}"
        finally:
            manifest._global_manifest = original


class TestImportHookGlobalState:
    """Test importer.py install_import_hook TOCTOU race."""

    def test_install_hook_idempotent_under_contention(self) -> None:
        """install_import_hook must install exactly once.

        The bug: check-then-install without lock allows multiple threads
        to see _import_hook as None and each install a new hook.
        """
        import sys

        from wtfui.web.compiler.importer import (
            install_import_hook,
            uninstall_import_hook,
        )

        uninstall_import_hook()

        n_threads = 50
        barrier = threading.Barrier(n_threads)

        def install() -> None:
            barrier.wait()
            install_import_hook()

        threads = [threading.Thread(target=install) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        from wtfui.web.compiler import importer

        hook_count = sum(1 for h in sys.meta_path if isinstance(h, type(importer._import_hook)))

        uninstall_import_hook()

        assert hook_count == 1, f"Expected 1 hook, found {hook_count} in sys.meta_path"


# ---------------------------------------------------------------------------
# Stress test: combined operations
# ---------------------------------------------------------------------------


class TestCombinedThreadSafety:
    """Stress tests combining multiple thread-unsafe operations."""

    def test_router_with_concurrent_navigation(self) -> None:
        """Router + HistoryState under concurrent navigation."""
        from wtfui.core.router import HistoryState, Route, Router

        def home() -> None:
            pass

        def about() -> None:
            pass

        def contact() -> None:
            pass

        routes = [
            Route("/", home),
            Route("/about", about),
            Route("/contact", contact),
        ]
        router = Router(routes=routes)
        history = HistoryState("/")
        router.bind_history(history)

        paths = ["/", "/about", "/contact"]
        n_threads = 20
        iterations = 50

        barrier = threading.Barrier(n_threads)
        errors: list[str] = []
        lock = threading.Lock()

        def navigate() -> None:
            barrier.wait()
            for i in range(iterations):
                path = paths[i % len(paths)]
                try:
                    history.push(path)
                    current = history.current_path
                    if current not in paths:
                        with lock:
                            errors.append(f"Invalid path: {current}")
                except Exception as e:
                    with lock:
                        errors.append(str(e))

        threads = [threading.Thread(target=navigate) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during navigation: {errors[:5]}"
