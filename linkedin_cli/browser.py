"""Playwright-based fallback automation for fragile LinkedIn write flows."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import random
import time
from typing import Iterable

from .auth import AuthSession
from .config import AppConfig


class BrowserActionError(RuntimeError):
    """Raised when browser fallback cannot complete an action."""


@dataclass(frozen=True)
class BrowserActionResult:
    """Simple browser mutation outcome."""

    success: bool
    detail: str


class LinkedInBrowserFallback:
    """Execute LinkedIn mutations through the browser when HTTP flows are unavailable."""

    def __init__(self, auth_session: AuthSession, config: AppConfig) -> None:
        self.auth_session = auth_session
        self.config = config

    def create_post(self, text: str, visibility: str) -> BrowserActionResult:
        with self._open_page("https://www.linkedin.com/feed/") as page:
            self._click_first(
                page,
                [
                    "button:has-text('Start a post')",
                    "[aria-label*='Start a post']",
                    "button.share-box-feed-entry__trigger",
                ],
            )
            composer = self._locator_for(
                page,
                ["[role='dialog'] [contenteditable='true']", "div[contenteditable='true']"],
            )
            composer.click()
            page.keyboard.type(text)
            if visibility and visibility != "connections":
                self._set_visibility(page, visibility)
            self._pause_for_write()
            self._click_first(
                page,
                [
                    "[role='dialog'] button:has-text('Post')",
                    "button.share-actions__primary-action",
                ],
            )
        return BrowserActionResult(True, "Post created through browser fallback.")

    def comment_on_post(self, activity_identifier: str, text: str) -> BrowserActionResult:
        with self._open_page(_activity_url(activity_identifier)) as page:
            self._click_first(
                page,
                [
                    "button[aria-label*='Comment']",
                    "button:has-text('Comment')",
                ],
                optional=True,
            )
            editor = self._locator_for(
                page,
                [
                    "form.comments-comment-box__form [contenteditable='true']",
                    ".comments-comment-box__form-container [contenteditable='true']",
                    "[role='textbox'][contenteditable='true']",
                ],
            )
            editor.click()
            page.keyboard.type(text)
            self._pause_for_write()
            self._click_first(
                page,
                [
                    "button.comments-comment-box__submit-button--cr",
                    "button:has-text('Post comment')",
                    "button:has-text('Comment')",
                ],
            )
        return BrowserActionResult(True, "Comment posted through browser fallback.")

    def toggle_save(self, activity_identifier: str, should_save: bool) -> BrowserActionResult:
        label = "Save" if should_save else "Unsave"
        with self._open_page(_activity_url(activity_identifier)) as page:
            self._click_first(
                page,
                [
                    "button[aria-label*='More actions']",
                    "button.feed-shared-control-menu__trigger",
                    "button[aria-label*='Open control menu']",
                ],
            )
            self._click_first(
                page,
                [
                    f"[role='menuitem']:has-text('{label}')",
                    f"div[role='menuitem']:has-text('{label}')",
                    f"button:has-text('{label}')",
                ],
            )
        verb = "saved" if should_save else "removed from saved items"
        return BrowserActionResult(True, f"Post {verb} through browser fallback.")

    def toggle_reaction(
        self,
        activity_identifier: str,
        reaction: str,
        *,
        remove: bool = False,
    ) -> BrowserActionResult:
        with self._open_page(_activity_url(activity_identifier)) as page:
            if remove:
                self._click_first(
                    page,
                    [
                        "button[aria-pressed='true'][aria-label*='reaction']",
                        "button.react-button--active",
                        "button.reactions-react-button[aria-pressed='true']",
                    ],
                )
                return BrowserActionResult(True, "Reaction removed through browser fallback.")

            if reaction.lower() == "like":
                self._click_first(
                    page,
                    [
                        "button[aria-label*='Like']",
                        "button:has-text('Like')",
                        "button.reactions-react-button",
                    ],
                )
                return BrowserActionResult(True, "Reaction applied through browser fallback.")

            raise BrowserActionError(
                f"Browser fallback currently supports removing reactions and applying 'like'; got '{reaction}'."
            )

    @contextmanager
    def _open_page(self, url: str):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - guarded by packaging
            raise BrowserActionError(
                "Playwright is not installed. Install it to enable browser fallback."
            ) from exc

        timeout_ms = int(self.config.rate_limit.timeout * 1000)
        with sync_playwright() as playwright:
            if self.config.browser.preferred == "firefox":
                browser = playwright.firefox.launch(headless=self.config.browser.headless)
            elif self.config.browser.preferred == "edge":
                browser = playwright.chromium.launch(channel="msedge", headless=self.config.browser.headless)
            else:
                browser = playwright.chromium.launch(headless=self.config.browser.headless)

            context = browser.new_context()
            context.add_cookies(self.auth_session.as_playwright_cookies())
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            yield page
            context.close()
            browser.close()

    def _set_visibility(self, page, visibility: str) -> None:
        label = "Anyone" if visibility == "public" else "Connections only"
        self._click_first(
            page,
            [
                "[role='dialog'] button[aria-label*='Post setting']",
                "[role='dialog'] button:has-text('Anyone')",
                "[role='dialog'] button:has-text('Connections only')",
            ],
            optional=True,
        )
        self._click_first(
            page,
            [
                f"[role='dialog'] label:has-text('{label}')",
                f"[role='dialog'] div:has-text('{label}')",
                f"[role='dialog'] span:has-text('{label}')",
            ],
            optional=True,
        )
        self._click_first(
            page,
            [
                "[role='dialog'] button:has-text('Done')",
                "[role='dialog'] button:has-text('Save')",
            ],
            optional=True,
        )

    def _click_first(self, page, selectors: Iterable[str], optional: bool = False) -> None:
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count():
                locator.first.click()
                return
        if not optional:
            raise BrowserActionError(f"Unable to locate LinkedIn UI control for selectors: {selectors}")

    def _locator_for(self, page, selectors: Iterable[str]):
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count():
                return locator.first
        raise BrowserActionError(f"Unable to locate LinkedIn editor for selectors: {selectors}")

    def _pause_for_write(self) -> None:
        delay = random.uniform(
            self.config.rate_limit.write_delay_min,
            self.config.rate_limit.write_delay_max,
        )
        time.sleep(delay)


def _activity_url(activity_identifier: str) -> str:
    if activity_identifier.startswith("http://") or activity_identifier.startswith("https://"):
        return activity_identifier
    if activity_identifier.startswith("urn:li:activity:"):
        activity_identifier = activity_identifier.split(":")[-1]
    return f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_identifier}/"
