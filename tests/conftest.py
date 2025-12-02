"""Pytest configuration and fixtures for Flow tests."""

import pytest


@pytest.fixture
def clean_state():
    """Ensure clean state between tests."""
    # Will be expanded as we add more stateful components
    yield
