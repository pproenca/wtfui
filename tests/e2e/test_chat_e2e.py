"""E2E tests for Chat app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Page


def test_chat_login_screen(page: Page, chat_server: str) -> None:
    """Verify login screen displays."""
    page.goto(chat_server)
    expect(page.locator("text=Welcome to Flow Chat")).to_be_visible()
    expect(page.locator('input[placeholder="Username"]')).to_be_visible()


def test_chat_login_flow(page: Page, chat_server: str) -> None:
    """Verify user can log in."""
    page.goto(chat_server)

    # Enter username
    page.fill('input[placeholder="Username"]', "TestUser")
    page.click('button:has-text("Join")')

    # Verify chat screen appears
    expect(page.locator("text=Flow Chat - TestUser")).to_be_visible()


def test_send_message(page: Page, chat_server: str) -> None:
    """Verify sending a message."""
    page.goto(chat_server)

    # Log in
    page.fill('input[placeholder="Username"]', "Alice")
    page.click('button:has-text("Join")')

    # Send message
    page.fill('input[placeholder="Type a message..."]', "Hello world!")
    page.click('button:has-text("Send")')

    # Verify message appears
    expect(page.locator("text=Hello world!")).to_be_visible()


def test_message_shows_timestamp(page: Page, chat_server: str) -> None:
    """Verify messages show timestamp."""
    page.goto(chat_server)

    # Log in and send message
    page.fill('input[placeholder="Username"]', "Bob")
    page.click('button:has-text("Join")')
    page.fill('input[placeholder="Type a message..."]', "Time test")
    page.click('button:has-text("Send")')

    # Verify timestamp format (HH:MM)
    expect(page.locator("text=/\\d{2}:\\d{2}/")).to_be_visible()
