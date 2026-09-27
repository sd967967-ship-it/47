"""
47 browser automation — Playwright (local Chromium, persistent profile).
Pattern from Playwright-based assistants: browser runs as a local subprocess,
CDP stays on 127.0.0.1, no hosted browser service. All functions are
on-demand (user asked), never background scraping.
Optional: pip install playwright && playwright install chromium
"""
import os
from pathlib import Path

_PROFILE = Path(__file__).parent / ".47_browser_profile"
_PROFILE.mkdir(exist_ok=True)


def _launch(headless: bool = True):
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch_persistent_context(
        str(_PROFILE), headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
    )
    return pw, browser


def open_page(url: str, headless: bool = True, wait_ms: int = 2500) -> str:
    """Open a page locally and return its title + first 2000 chars of text."""
    if not url.lower().startswith(("http://", "https://")):
        return "Give me a full http(s) URL."
    pw, ctx = _launch(headless)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, timeout=20000)
        page.wait_for_timeout(wait_ms)
        title = page.title()
        text = page.inner_text("body")[:2000]
        return f"{title}\n\n{text}"
    except Exception as e:
        return f"Couldn't open {url}: {e}"
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


def search_web(query: str) -> str:
    """DuckDuckGo search rendered locally (JS-capable fallback to actions.web_search)."""
    from urllib.parse import quote_plus
    return open_page(f"https://duckduckgo.com/html/?q={quote_plus(query)}")
