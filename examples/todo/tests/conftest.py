"""Pytest configuration for todo app tests."""

import pytest


@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """Reset scheduler state before each test to prevent test pollution."""
    from wtfui.core.scheduler import reset_scheduler

    reset_scheduler()
    yield
    reset_scheduler()
