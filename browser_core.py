"""
browser_core.py — Stealth browser initialization & human-emulation layer.

Provides:
  - Headless browser with stealth patches
  - Media-blocking (images, video, css) for zero CPU
  - Human-like scrolling with Bezier jitter
  - Captcha/block detection + headed-browser recovery
"""
import asyncio
import logging
import math
import random
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    Route,
    async_playwright,
)
from playwright_stealth import Stealth  # type: ignore[import-untyped]

log = logging.getLogger(__name__)

STORAGE_PATH = Path(__file__).parent / "storage_state.json"

# Extensions that carry heavy payloads — block them
BLOCKED_RESOURCE_TYPES = {"image", "media"}
BLOCKED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".svg")


async def _block_media(route: Route) -> None:
    """Abort requests for heavy media resources."""
    url = route.request.url.lower()
    rtype = route.request.resource_type
    if rtype in BLOCKED_RESOURCE_TYPES or any(url.endswith(ext) for ext in BLOCKED_EXTENSIONS):
        await route.abort()
    else:
        await route.continue_()


def _bezier_point(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Compute a cubic Bezier value at parameter t."""
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t ** 2 * p2
        + t ** 3 * p3
    )


class StealthBrowser:
    """Manages a stealth Playwright browser context."""

    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._headed_mode = False

    # ── lifecycle ────────────────────────────────────

    async def launch(self, headless: bool = True, hidden: bool = False) -> Page:
        """Launch browser, apply stealth, block media, return page."""
        self._pw = await async_playwright().start()

        storage_exists = STORAGE_PATH.exists()
        if not storage_exists:
            log.warning("storage_state.json not found — run auth.py first!")

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
        if hidden and not headless:
            args.append("--window-position=-32000,-32000")

        browser = await self._pw.chromium.launch(
            headless=headless,
            args=args,
        )

        ctx_kwargs: dict = {
            "viewport": {"width": 1440, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        if storage_exists:
            ctx_kwargs["storage_state"] = str(STORAGE_PATH)

        stealth = Stealth()
        self._context = await browser.new_context(**ctx_kwargs)
        self._context.set_default_navigation_timeout(90000)
        self._context.set_default_timeout(60000)
        self._page = await self._context.new_page()

        # Apply stealth patches
        await stealth.apply_stealth_async(self._page)

        # Block heavy resources
        await self._page.route("**/*", _block_media)

        log.info(f"Browser launched (headless={headless})")
        return self._page

    async def rescue_window(self):
        """Returns the window position back to viewable area with micro-size as requested."""
        if not getattr(self, "_context", None) or not getattr(self, "_page", None):
            return
            
        try:
            session = await self._context.new_cdp_session(self._page)
            target_info = await session.send("Target.getTargetInfo")
            res = await session.send("Browser.getWindowForTarget", {"targetId": target_info["targetInfo"]["targetId"]})
            window_id = res["windowId"]
            
            await session.send("Browser.setWindowBounds", {
                "windowId": window_id,
                "bounds": {
                    "left": 40,
                    "top": 40,
                    "width": 300,
                    "height": 300,
                    "windowState": "normal"
                }
            })
            # Small delay so user visually sees the window return just before closing
            import asyncio
            await asyncio.sleep(1)
        except Exception as e:
            log.debug(f"Failed to rescue window: {e}")

    async def close(self) -> None:
        """Tear down browser + playwright."""
        try:
            if self._context:
                # Save refreshed session state (cookies, localstorage)
                await self._context.storage_state(path=str(STORAGE_PATH))
                await self._context.close()
        except Exception:
            pass
        try:
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
        log.info("Browser closed.")

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._context

    # ── human emulation ──────────────────────────────

    async def human_delay(self, lo: float = 1.0, hi: float = 3.5) -> None:
        """Sleep for a randomised, human-plausible interval."""
        await asyncio.sleep(random.uniform(lo, hi))

    async def human_scroll(self, page: Optional[Page] = None, times: int = 1) -> None:
        """Scroll down with Bezier-curved jitter to simulate a real finger flick."""
        p = page or self.page
        for _ in range(times):
            distance = random.randint(700, 1100)
            steps = random.randint(6, 14)
            # Center mouse so wheel events hit the main content area
            viewport = p.viewport_size
            if viewport:
                await p.mouse.move(viewport["width"] / 2, viewport["height"] / 2)
            
            # Bezier control points for a natural scroll curve
            p0, p3 = 0.0, float(distance)
            p1 = p0 + random.uniform(0.2, 0.5) * distance
            p2 = p3 - random.uniform(0.1, 0.3) * distance
            prev_y = 0.0
            for i in range(1, steps + 1):
                t = i / steps
                y = _bezier_point(t, p0, p1, p2, p3)
                delta = y - prev_y
                await p.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.01, 0.05))
                prev_y = y
            # Guarantee scroll with keyboard on Desktop
            await p.keyboard.press("PageDown")
            # Post-scroll pause
            await asyncio.sleep(random.uniform(0.5, 1.8))

    async def human_move_mouse(self, page: Optional[Page] = None) -> None:
        """Random mouse movement to spoof idle-detection."""
        p = page or self.page
        x = random.randint(50, 380)
        y = random.randint(100, 800)
        await p.mouse.move(x, y, steps=random.randint(5, 15))

    # ── captcha/block recovery ───────────────────────

    async def check_challenge(self, page: Optional[Page] = None) -> bool:
        """
        Returns True if Instagram has issued a challenge
        (captcha / suspicious-activity block).
        """
        p = page or self.page
        url = p.url
        return "/challenge/" in url or "/suspicious/" in url

    async def handle_challenge(self, collected_data: list) -> None:
        """
        Emergency protocol:
         1. Save whatever data we have so far
         2. Re-open browser in headed mode for manual captcha solving
         3. Wait for user input in terminal
         4. Persist new session
        """
        log.warning("⚠️  CHALLENGE DETECTED — entering recovery mode")

        # 1. Emergency save
        import json
        emergency_path = Path(__file__).parent / "emergency_backup.json"
        with open(emergency_path, "w", encoding="utf-8") as f:
            json.dump(collected_data, f, ensure_ascii=False, indent=2)
        log.info(f"Emergency data saved to {emergency_path} ({len(collected_data)} items)")

        # 2. Close current headless context
        await self.close()

        # 3. Relaunch in headed mode
        print("\a")  # Terminal bell
        log.warning("🔔 Browser re-opened in headed mode. Solve the captcha, then come back here.")
        page = await self.launch(headless=False)
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")

        # 4. Wait for manual resolution
        input(">>> Press ENTER after solving the captcha in the browser window... ")

        # 5. Save refreshed session
        await self.context.storage_state(path=str(STORAGE_PATH))
        log.info("✅ Session refreshed after captcha solve.")

        # 6. Close headed and return to headless
        await self.close()
        self._headed_mode = False
