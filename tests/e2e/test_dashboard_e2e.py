"""E2E tests for Dashboard app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


def test_dashboard_loads(page: Page, dashboard_server: str) -> None:
    """Verify dashboard loads with metrics."""
    page.goto(dashboard_server)
    expect(page.locator("text=Flow Dashboard")).to_be_visible()
    expect(page.locator("text=Total Sales")).to_be_visible()


def test_sidebar_navigation(page: Page, dashboard_server: str) -> None:
    """Verify sidebar navigation works."""
    page.goto(dashboard_server)

    # Click Analytics
    page.click('button:has-text("Analytics")')

    # Verify page indicator updates
    expect(page.locator("text=Page: Analytics")).to_be_visible()


def test_metrics_display(page: Page, dashboard_server: str) -> None:
    """Verify metric cards display values."""
    page.goto(dashboard_server)

    # Check all metric cards are visible
    expect(page.locator("text=Total Sales")).to_be_visible()
    expect(page.locator("text=Average Sale")).to_be_visible()
    expect(page.locator("text=Active Users")).to_be_visible()
    expect(page.locator("text=Conversion")).to_be_visible()
