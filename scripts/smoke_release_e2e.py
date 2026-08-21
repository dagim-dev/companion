#!/usr/bin/env python3
"""Production-like browser smoke test for V4 release.

Requires:
  pip install playwright
  playwright install chromium

Usage:
  FRONTEND_URL=http://127.0.0.1:3001 python scripts/smoke_release_e2e.py
"""

from __future__ import annotations

import os
import sys
import time

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    print("FAIL [setup]: install playwright with `pip install playwright`", file=sys.stderr)
    raise SystemExit(1)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3001")
STAMP = int(time.time())
EMAIL = f"smoke-ui-{STAMP}@example.com"
PASSWORD = "smoke-pass-12345"
CHAT_MESSAGE = "V4 browser smoke test message."


def fail(step: str, detail: str) -> None:
    print(f"FAIL [{step}]: {detail}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(FRONTEND_URL, wait_until="networkidle")

            page.get_by_role("button", name="Need an account? Register").click()
            page.get_by_label("Email").fill(EMAIL)
            page.get_by_label("Password").fill(PASSWORD)
            page.get_by_role("button", name="Register").click()

            page.get_by_role("button", name="Continue").first.click()
            page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Continue").click()

            page.get_by_placeholder("Name or title, e.g. Alex or Captain").fill("Smoke")
            page.get_by_role("button", name="Next").click()
            page.get_by_text("Addressing you as:").wait_for(timeout=10_000)
            page.get_by_role("button", name="Start chatting").click()

            page.get_by_placeholder("Message NOVA…").wait_for(timeout=15_000)
            page.get_by_placeholder("Message NOVA…").fill(CHAT_MESSAGE)
            page.get_by_role("button", name="Send").click()

            page.get_by_text(CHAT_MESSAGE, exact=True).wait_for(timeout=15_000)
            assistant = page.locator("p.whitespace-pre-wrap").filter(has_not_text=CHAT_MESSAGE).last
            for _ in range(60):
                text = (assistant.text_content() or "").strip()
                if text and text != "\u00a0":
                    break
                page.wait_for_timeout(1_000)
            else:
                fail("stream", "assistant response did not render")

            page.reload(wait_until="networkidle")
            page.get_by_text(CHAT_MESSAGE, exact=True).wait_for(timeout=15_000)
            restored = page.locator("p.whitespace-pre-wrap").filter(has_not_text=CHAT_MESSAGE).last
            for _ in range(15):
                text = (restored.text_content() or "").strip()
                if text and text != "\u00a0":
                    break
                page.wait_for_timeout(1_000)
            else:
                fail("refresh", "transcript was not restored after refresh")

            page.get_by_role("button", name="Sign out").click()
            page.get_by_label("Email").wait_for(timeout=10_000)

            page.get_by_label("Email").fill(EMAIL)
            page.get_by_label("Password").fill(PASSWORD)
            page.get_by_role("button", name="Sign in").click()

            page.get_by_placeholder("Message NOVA…").wait_for(timeout=15_000)
            page.get_by_text(CHAT_MESSAGE, exact=True).wait_for(timeout=15_000)
        except PlaywrightTimeoutError as exc:
            snippet = page.locator("body").inner_text()[-1200:]
            fail("unexpected", f"{exc}\n--- page tail ---\n{snippet}")
        finally:
            browser.close()

    print("PASS register")
    print("PASS onboard")
    print("PASS stream")
    print("PASS refresh_transcript")
    print("PASS sign_in_again")


if __name__ == "__main__":
    main()
