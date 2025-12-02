"""E2E tests for Todo app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


def test_todo_app_loads(page: Page, todo_server: str) -> None:
    """Verify app loads and displays title."""
    page.goto(todo_server)
    expect(page.locator("text=Flow Todo App")).to_be_visible()


def test_add_todo(page: Page, todo_server: str) -> None:
    """Verify adding a todo item."""
    page.goto(todo_server)

    # Type todo text
    page.fill('input[placeholder="What needs to be done?"]', "Buy milk")

    # Click Add button
    page.click('button:has-text("Add")')

    # Verify todo appears
    expect(page.locator("text=Buy milk")).to_be_visible()


def test_toggle_todo(page: Page, todo_server: str) -> None:
    """Verify toggling todo completion."""
    page.goto(todo_server)

    # Add a todo
    page.fill('input[placeholder="What needs to be done?"]', "Test todo")
    page.click('button:has-text("Add")')

    # Wait for todo to appear
    expect(page.locator("text=Test todo")).to_be_visible()

    # Click toggle button (the circle button - Unicode ○)
    page.click('button:has-text("○")')

    # Verify it's now checked (checkmark - Unicode ✓)
    expect(page.locator('button:has-text("✓")')).to_be_visible()


def test_delete_todo(page: Page, todo_server: str) -> None:
    """Verify deleting a todo."""
    page.goto(todo_server)

    # Add a todo
    page.fill('input[placeholder="What needs to be done?"]', "Delete me")
    page.click('button:has-text("Add")')

    # Wait for todo to appear
    expect(page.locator("text=Delete me")).to_be_visible()

    # Delete it - click the x button that's the sibling following "Delete me" text
    # The text and x button are siblings in the same HStack row
    page.locator("text=Delete me").locator("xpath=following-sibling::button[1]").click()

    # Verify it's gone
    expect(page.locator("text=Delete me")).not_to_be_visible()
