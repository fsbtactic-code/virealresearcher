"""
skills.py — The 5 MCP skills + virality math.

Skills:
  1. expand_search_keywords  — autocomplete suggestions
  2. scrape_feed             — home feed (reels+carousels)
  3. scrape_explore          — explore tab
  4. scrape_search           — keyword search
  5. master_viral_hunter     — orchestrator + virality ranking
"""
import asyncio
import json
import logging
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from browser_core import StealthBrowser
from interceptor import (
    InterceptorState,
    PostData,
    PostFilter,
    extract_search_suggestions,
    handle_response,
)
from ui_generator import generate_results_html

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def dismiss_instagram_modals(page) -> None:
    """Silently close Instagram pop-ups that break scrolling.

    Handles:
    - 'Turn on notifications' dialog
    - Cookie / GDPR banners
    - 'Save your login info?' prompt
    - 'Add to home screen' sheet
    - Any generic overlay 'Not Now' / 'Dismiss' / 'Close' button
    """
    DISMISS_JS = """
    (() => {
        const texts = [
            'not now', '\u043d\u0435 \u0441\u0435\u0439\u0447\u0430\u0441', '\u043f\u043e\u0437\u0436\u0435',
            'dismiss', 'close', '\u0437\u0430\u043a\u0440\u044b\u0442\u044c',
            'cancel', '\u043e\u0442\u043c\u0435\u043d\u0430',
            'allow', '\u0440\u0430\u0437\u0440\u0435\u0448\u0438\u0442\u044c',
            'accept all', '\u043f\u0440\u0438\u043d\u044f\u0442\u044c \u0432\u0441\u0435',
            'only allow essential',
        ];
        let closed = 0;
        const dialogs = document.querySelectorAll(
            '[role="dialog"], [role="alertdialog"], .x1vjfegm, ._a9-z, ._ac7v'
        );
        dialogs.forEach(dialog => {
            dialog.querySelectorAll('button, [role="button"]').forEach(btn => {
                const t = (btn.innerText || '').toLowerCase().trim();
                if (texts.some(x => t === x || t.startsWith(x))) { btn.click(); closed++; }
            });
        });
        if (closed === 0) {
            document.querySelectorAll('button, [role="button"]').forEach(btn => {
                const t = (btn.innerText || '').toLowerCase().trim();
                if (t === 'allow' || t === '\u0440\u0430\u0437\u0440\u0435\u0448\u0438\u0442\u044c' ||
                    t === 'accept all' || t === 'not now' ||
                    t === '\u043d\u0435 \u0441\u0435\u0439\u0447\u0430\u0441' || t === 'dismiss') {
                    btn.click(); closed++;
                }
            });
        }
        return closed;
    })()
    """
    try:
        closed = await page.evaluate(DISMISS_JS)
        if closed:
            log.debug(f"[modal] dismissed {closed} Instagram modal(s)")
    except Exception:
        pass  # page may be navigating — silently skip



async def safe_goto(page, url: str, retries: int = 3, timeout: int = 45000):
    """
    Navigate to a URL using a 'fast commit' + 'selector polling' approach.
    More resilient for VPN/Slow connections than waiting for full load.
    """
    # Selectors that indicate the page is functionally loaded
    selectors = [
        'main[role="main"]',
        'article',
        'input[name="username"]',
        'nav[role="navigation"]',
        'div[style*="grid-template-columns"]'
    ]
    
    for attempt in range(retries):
        try:
            log.info(f"Navigating to {url} (attempt {attempt+1}/{retries})...")
            # Wait only for headers/commit
            await page.goto(url, wait_until="commit", timeout=20000)
            
            log.info(f"Polling for DOM content (limit {timeout/1000}s)...")
            try:
                # wait_for_selector internally polls the DOM
                await page.wait_for_selector(
                    ", ".join(selectors),
                    state="attached",
                    timeout=timeout
                )
                log.info(f"✅ DOM content detected.")
                return True
            except Exception:
                raise Exception("Functional selectors did not appear in time.")

        except Exception as exc:
            log.warning(f"Attempt {attempt+1} failed for {url}: {exc}")
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(5, 10))
            else:
                log.error(f"All {retries} attempts failed for {url}")
                raise
    return False


def _hours_ago(ts: int) -> float:
    if ts <= 0:
        return 999.0
    return max((time.time() - ts) / 3600, 0.01)


def compute_velocity(post: PostData) -> float:
    """Velocity = (Likes + Comments*2 + Views*0.5) / Hours. Views only for Reels."""
    hours = _hours_ago(post.timestamp)
    view_component = post.views * 0.5 if post.is_reel else 0.0
    raw = post.likes + post.comments * 2 + view_component
    return round(raw / hours, 2)


async def auto_like_new_posts(page: Any, state: InterceptorState, global_state: Optional[InterceptorState], prev_count: int, max_likes: int = 20):
    g_state = global_state if global_state else state
    if g_state.liked_count >= max_likes:
        return
        
    new_posts = state.posts[prev_count:]
    for p in new_posts:
        if g_state.liked_count >= max_likes:
            break
        if not p.shortcode:
            continue
            
        try:
            import asyncio, random
            # 1) Пытаемся найти пост как статью в ленте (Feed)
            article_loc = page.locator(f"article:has(a[href*='/{p.shortcode}/'])").first
            if await article_loc.count() > 0:
                like_svg = article_loc.locator("svg[aria-label='Нравится'], svg[aria-label='Like']").first
                if await like_svg.count() > 0:
                    btn = like_svg.locator("..").first
                    await btn.click()
                    g_state.liked_count += 1
                    log.info(f"[auto_like] ❤️ Liked '{p.shortcode}' from feed (Total: {g_state.liked_count}/{max_likes})")
                    await asyncio.sleep(random.uniform(0.7, 1.3))
                continue

            # 2) Пытаемся найти пост как сетку (Explore / Search)
            grid_link = page.locator(f"a[href*='/{p.shortcode}/']").first
            if await grid_link.count() > 0:
                await grid_link.scroll_into_view_if_needed()
                await grid_link.click(delay=140)
                
                # Ждем открытия модалки
                dialog = page.locator("div[role='dialog']").first
                try:
                    await dialog.wait_for(state="visible", timeout=4000)
                    like_svg = dialog.locator("svg[aria-label='Нравится'], svg[aria-label='Like']").first
                    if await like_svg.count() > 0:
                        btn = like_svg.locator("..").first
                        await btn.click(delay=180)
                        g_state.liked_count += 1
                        log.info(f"[auto_like] ❤️ Liked '{p.shortcode}' from grid (Total: {g_state.liked_count}/{max_likes})")
                        await asyncio.sleep(random.uniform(0.7, 1.3))
                except Exception:
                    pass
                finally:
                    # Закрываем модалку кнопкой Escape
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(random.uniform(0.5, 0.9))

        except Exception as e:
            log.debug(f"[auto_like] error on {p.shortcode}: {e}")

def _serialize_posts(posts: list[PostData]) -> list[dict]:
    results = []
    for p in posts:
        d = asdict(p)
        d["velocity_score"] = compute_velocity(p)
        d["hours_ago"] = round(_hours_ago(p.timestamp), 1)
        results.append(d)
    return results


def _save_progress(posts: list[PostData], label: str) -> Path:
    path = OUTPUT_DIR / f"{label}_{int(time.time())}.json"
    data = _serialize_posts(posts)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"Progress saved: {path} ({len(data)} posts)")
    return path


def _is_within_time_limit(state: InterceptorState, time_limit_hours: int) -> bool:
    if state.oldest_timestamp == 0:
        return True
    hours = _hours_ago(state.oldest_timestamp)
    return hours <= time_limit_hours


def _build_filter(
    min_likes: int = 0, max_likes: int = 0,
    min_comments: int = 0, max_comments: int = 0,
    max_followers: int = 0, min_followers: int = 0,
    exclude_zero_engagement: bool = False,
) -> Optional[PostFilter]:
    """Build a PostFilter if any criteria are set, otherwise None."""
    f = PostFilter(
        min_likes=min_likes, max_likes=max_likes,
        min_comments=min_comments, max_comments=max_comments,
        max_followers=max_followers, min_followers=min_followers,
        exclude_zero_engagement=exclude_zero_engagement,
    )
    # Return None if everything is default (no filtering)
    if (f.min_likes == 0 and f.max_likes == 0 and f.min_comments == 0
            and f.max_comments == 0 and f.max_followers == 0
            and f.min_followers == 0 and not f.exclude_zero_engagement):
        return None
    return f


# ═══════════════════════════════════════════════════════
#  Skill 1: expand_search_keywords
# ═══════════════════════════════════════════════════════

async def expand_search_keywords(seed_keyword: str) -> list[str]:
    log.info(f"[expand_search_keywords] Seed: {seed_keyword}")
    browser = StealthBrowser()
    suggestions: list[str] = []
    try:
        page = await browser.launch(headless=False, hidden=True)
        await safe_goto(page, "https://www.instagram.com/")
        await browser.human_delay(2, 4)

        captured_data: list[dict] = []

        async def _on_autocomplete(response) -> None:
            url = response.url
            if "web/search/topsearch" in url or "web_search_typeahead" in url:
                try:
                    body = await response.body()
                    data = json.loads(body.decode("utf-8", errors="replace"))
                    captured_data.append(data)
                except Exception:
                    pass

        page.on("response", _on_autocomplete)
        await safe_goto(page, "https://www.instagram.com/explore/")
        await browser.human_delay(1.5, 3)

        search_selectors = [
            'input[placeholder*="Search"]', 'input[aria-label*="Search"]',
            '[role="search"] input', 'input[type="text"]',
        ]
        search_input = None
        for sel in search_selectors:
            try:
                search_input = await page.wait_for_selector(sel, timeout=3000)
                if search_input:
                    break
            except Exception:
                continue

        if search_input:
            await search_input.click()
            await browser.human_delay(0.5, 1)
            for char in seed_keyword:
                await search_input.type(char, delay=random.randint(80, 200))
                await asyncio.sleep(random.uniform(0.3, 0.8))
            await asyncio.sleep(2)

        for data in captured_data:
            suggestions.extend(extract_search_suggestions(data))
        suggestions = list(dict.fromkeys(suggestions))[:15]
        log.info(f"[expand_search_keywords] Found {len(suggestions)} suggestions")
    except Exception as exc:
        log.error(f"[expand_search_keywords] Error: {exc}")
    finally:
        await browser.rescue_window()
        await browser.close()
    return suggestions


# ═══════════════════════════════════════════════════════
#  Skill 2: scrape_feed
# ═══════════════════════════════════════════════════════

async def scrape_feed(
    time_limit_hours: int = 24,
    max_posts: int = 40,
    post_filter: Optional[PostFilter] = None,
    scrolls_limit: int = 60,
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True,
    progress_cb: Optional[Any] = None,
    stop_event: Optional[Any] = None,
    global_state: Optional[InterceptorState] = None
) -> list[dict]:
    log.info(f"[scrape_feed] Starting (limit: {time_limit_hours}h)")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False, hidden=True)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source="feed", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter, progress_cb=progress_cb, global_state=global_state)
        ))
        await safe_goto(page, "https://www.instagram.com/")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = scrolls_limit, 0
        recovery_attempted = False
        DOM_SEL = "article, a[href*='/p/']"
        for i in range(max_scrolls):
            if stop_event and stop_event.is_set():
                log.warning("[scrape_feed] Stop request received. Exiting loop.")
                break
            prev_count = len(state.posts)
            prev_filtered = state.filtered_out
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

            # ── Dismiss any modal pop-ups before scrolling ──
            await dismiss_instagram_modals(page)
            await auto_like_new_posts(page, state, global_state, prev_count, max_likes=20)

            # ── Scroll to the absolute bottom so IG's IntersectionObserver fires ──
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.8, 1.4))
            # Second nudge — some IG layouts need this to commit the sentinel
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            log.debug(f"[feed] scroll {i+1}/{max_scrolls} — DOM before: {prev_dom}, API posts: {prev_count}")

            # ── Wait up to 20s for new DOM nodes OR new API interceptions ──
            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 20:
                if stop_event and stop_event.is_set():
                    break
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom or state.filtered_out > prev_filtered:
                    batch_loaded = True
                    # Give a tiny grace period for remaining items in the batch
                    await asyncio.sleep(1.5)
                    break

            curr_dom_final = 0
            try:
                curr_dom_final = await page.locator(DOM_SEL).count()
            except Exception:
                pass

            log.info(f"[feed] scroll {i+1} done — DOM: {prev_dom}→{curr_dom_final}, API posts: {prev_count}→{len(state.posts)}, batch_loaded={batch_loaded}")

            if not batch_loaded:
                log.info(f"[scrape_feed] No new content after 20s. Will try one more scroll.")



            if random.random() < 0.3:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break

            if len(state.posts) >= max_posts:
                log.info(f"[scrape_feed] Reached max_posts ({max_posts}), stopping.")
                break

            no_new = no_new + 1 if len(state.posts) == prev_count and state.filtered_out == prev_filtered else 0
            if no_new >= 8 and curr_dom_final == prev_dom:
                if not recovery_attempted:
                    log.warning("[scrape_feed] Stalled >60s. Attempting recovery (dismiss, refresh)...")
                    await dismiss_instagram_modals(page)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(2)
                    try: await page.reload(timeout=30000)
                    except: pass
                    await browser.human_delay(3, 5)
                    recovery_attempted = True
                    no_new = 0
                    continue
                else:
                    log.warning(f"[scrape_feed] 8 consecutive scrolls with no new content. Stopping.")
                    break
            if (i + 1) % 20 == 0:
                _save_progress(state.posts, "feed")
    except Exception as exc:
        log.error(f"[scrape_feed] Error: {exc}")
        _save_progress(state.posts, "feed_error")
    finally:
        await browser.rescue_window()
        await browser.close()

    log.info(f"[scrape_feed] Done — {len(state.posts)} posts, {state.filtered_out} filtered out")
    return _serialize_posts(state.posts)


# ═══════════════════════════════════════════════════════
#  Skill 3: scrape_explore
# ═══════════════════════════════════════════════════════

async def scrape_explore(
    time_limit_hours: int = 24,
    max_posts: int = 80,
    post_filter: Optional[PostFilter] = None,
    scrolls_limit: int = 60,
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True,
    progress_cb: Optional[Any] = None,
    stop_event: Optional[Any] = None,
    global_state: Optional[InterceptorState] = None
) -> list[dict]:
    log.info(f"[scrape_explore] Starting (limit: {time_limit_hours}h)")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False, hidden=True)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source="explore", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter, progress_cb=progress_cb, global_state=global_state)
        ))
        await safe_goto(page, "https://www.instagram.com/explore/")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = scrolls_limit, 0
        recovery_attempted = False
        DOM_SEL = "article, div[style*='grid-template-columns'] a"
        for i in range(max_scrolls):
            if stop_event and stop_event.is_set():
                log.warning("[scrape_explore] Stop request received. Exiting loop.")
                break
            prev_count = len(state.posts)
            prev_filtered = state.filtered_out
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

            # ── Dismiss any modal pop-ups before scrolling ──
            await dismiss_instagram_modals(page)
            await auto_like_new_posts(page, state, global_state, prev_count, max_likes=20)

            # ── True bottom scroll — triggers IG's infinite-scroll loader ──
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.8, 1.4))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            log.debug(f"[explore] scroll {i+1}/{max_scrolls} — DOM before: {prev_dom}, API posts: {prev_count}")

            # ── Wait up to 20s for new DOM nodes OR new API interceptions ──
            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 20:
                if stop_event and stop_event.is_set():
                    break
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom or state.filtered_out > prev_filtered:
                    batch_loaded = True
                    await asyncio.sleep(1.5)
                    break

            curr_dom_final = 0
            try:
                curr_dom_final = await page.locator(DOM_SEL).count()
            except Exception:
                pass

            log.info(f"[explore] scroll {i+1} done — DOM: {prev_dom}→{curr_dom_final}, API posts: {prev_count}→{len(state.posts)}, batch_loaded={batch_loaded}")

            if not batch_loaded:
                log.info(f"[scrape_explore] No new content after 20s, will retry scroll.")



            if random.random() < 0.25:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break

            if len(state.posts) >= max_posts:
                log.info(f"[scrape_explore] Reached max_posts ({max_posts}), stopping.")
                break

            no_new = no_new + 1 if len(state.posts) == prev_count and state.filtered_out == prev_filtered else 0
            if no_new >= 8 and curr_dom_final == prev_dom:
                if not recovery_attempted:
                    log.warning("[scrape_explore] Stalled >60s. Attempting recovery (dismiss, refresh)...")
                    await dismiss_instagram_modals(page)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(2)
                    try: await page.reload(timeout=30000)
                    except: pass
                    await browser.human_delay(3, 5)
                    recovery_attempted = True
                    no_new = 0
                    continue
                else:
                    log.warning(f"[scrape_explore] 8 consecutive scrolls with no new content. Stopping.")
                    break
            if (i + 1) % 15 == 0:
                _save_progress(state.posts, "explore")
    except Exception as exc:
        log.error(f"[scrape_explore] Error: {exc}")
        _save_progress(state.posts, "explore_error")
    finally:
        await browser.rescue_window()
        await browser.close()

    log.info(f"[scrape_explore] Done — {len(state.posts)} posts, {state.filtered_out} filtered out")
    return _serialize_posts(state.posts)


# ═══════════════════════════════════════════════════════
#  Skill 4: scrape_search
# ═══════════════════════════════════════════════════════

async def scrape_search(
    keyword: str,
    time_limit_hours: int = 24,
    max_posts: int = 100,
    post_filter: Optional[PostFilter] = None,
    scrolls_limit: int = 12,
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True,
    progress_cb: Optional[Any] = None,
    stop_event: Optional[Any] = None,
    global_state: Optional[InterceptorState] = None
) -> list[dict]:
    log.info(f"[scrape_search] Keyword: '{keyword}' (limit: {time_limit_hours}h, max: {max_posts})")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False, hidden=True)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source=f"search:{keyword}", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter, progress_cb=progress_cb, global_state=global_state)
        ))
        clean_keyword = keyword.lstrip("#").strip()
        # New Global Search URL
        await safe_goto(page, f"https://www.instagram.com/explore/search/keyword/?q={clean_keyword}")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = scrolls_limit, 0
        recovery_attempted = False
        DOM_SEL = "a[href*='/p/'], a[href*='/reel/']"
        for i in range(max_scrolls):
            if stop_event and stop_event.is_set():
                log.warning(f"[scrape_search:{keyword}] Stop request received. Exiting loop.")
                break
            prev_count = len(state.posts)
            prev_filtered = state.filtered_out
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

            # ── Optimize Exploration ──
            await auto_like_new_posts(page, state, global_state, prev_count, max_likes=20)

            # ── Scroll to true bottom so IG's sentinel enters viewport ──
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.8, 1.4))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            log.debug(f"[search:{keyword}] scroll {i+1}/{max_scrolls} — DOM before: {prev_dom}, API posts: {prev_count}")

            # ── Wait up to 20s for new DOM nodes OR new API interceptions ──
            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 20:
                if stop_event and stop_event.is_set():
                    break
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom or state.filtered_out > prev_filtered:
                    batch_loaded = True
                    await asyncio.sleep(1.5)
                    break

            curr_dom_final = 0
            try:
                curr_dom_final = await page.locator(DOM_SEL).count()
            except Exception:
                pass

            log.info(f"[search:{keyword}] scroll {i+1} done — DOM: {prev_dom}→{curr_dom_final}, API posts: {prev_count}→{len(state.posts)}, batch_loaded={batch_loaded}")

            if not batch_loaded:
                log.info(f"[scrape_search] No new content after 20s, retrying...")



            if random.random() < 0.2:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                log.warning("[scrape_search] Hit captcha/challenge, breaking loop.")
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break
            if len(state.posts) >= max_posts:
                log.info(f"[scrape_search] Reached max_posts ({max_posts}), stopping.")
                break
            
            no_new = no_new + 1 if len(state.posts) == prev_count and state.filtered_out == prev_filtered else 0
            if no_new >= 6 and curr_dom_final == prev_dom:
                if not recovery_attempted:
                    log.warning('[scrape_loop] Stalled >60s. Attempting recovery (dismiss, refresh)...')
                    await dismiss_instagram_modals(page)
                    await page.evaluate('window.scrollTo(0, 0)')
                    await asyncio.sleep(2)
                    try: await page.reload(timeout=30000)
                    except: pass
                    await browser.human_delay(3, 5)
                    recovery_attempted = True
                    no_new = 0
                    continue
                else:
                    log.warning(f"[scrape_search] 6 scrolls with no new posts. Stopping.")
                    break
            log.debug(f"[search:{keyword}] no_new={no_new}, posts={len(state.posts)}")
    except Exception as exc:
        log.error(f"[scrape_search] Error: {exc}")
        _save_progress(state.posts, f"search_{clean_keyword}_error")
    finally:
        await browser.rescue_window()
        await browser.close()

    log.info(f"[scrape_search] Done — {len(state.posts)} posts for '{keyword}'")
    return _serialize_posts(state.posts)


# ═══════════════════════════════════════════════════════
#  Skill 4.5: scrape_search_tab (for concurrent runs)
# ═══════════════════════════════════════════════════════

async def scrape_search_tab(
    browser: StealthBrowser,
    page: Any,
    keyword: str,
    time_limit_hours: int = 24,
    max_posts: int = 100,
    post_filter: Optional[PostFilter] = None,
    scrolls_limit: int = 7,  # Default for bulk is 7
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True,
    progress_cb: Optional[Any] = None,
    stop_event: Optional[Any] = None,
    global_state: Optional[InterceptorState] = None
) -> list[dict]:
    log.info(f"[scrape_search_tab] Keyword: '{keyword}' (scrolls limit: {scrolls_limit})")
    state = InterceptorState()
    
    async def _on_resp(r):
        await handle_response(r, state, source=f"search:{keyword}", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter, progress_cb=progress_cb, global_state=global_state)
    
    page.on("response", lambda r: asyncio.ensure_future(_on_resp(r)))
    
    try:
        clean_keyword = keyword.lstrip("#").strip()
        await safe_goto(page, f"https://www.instagram.com/explore/search/keyword/?q={clean_keyword}")
        await browser.human_delay(2, 4)

        max_scrolls = scrolls_limit
        no_new = 0
        recovery_attempted = False
        DOM_SEL = "a[href*='/p/'], a[href*='/reel/']"
        
        for i in range(max_scrolls):
            if stop_event and stop_event.is_set():
                break
            prev_count = len(state.posts)
            prev_filtered = state.filtered_out
            try: prev_dom = await page.locator(DOM_SEL).count()
            except: prev_dom = 0

            await dismiss_instagram_modals(page)
            await auto_like_new_posts(page, state, global_state, prev_count, max_likes=20)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.6, 1.2))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 15:
                if stop_event and stop_event.is_set(): break
                await asyncio.sleep(0.8)
                try: curr_dom = await page.locator(DOM_SEL).count()
                except: curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom or state.filtered_out > prev_filtered:
                    batch_loaded = True
                    await asyncio.sleep(1.0)
                    break

            try: curr_dom_final = await page.locator(DOM_SEL).count()
            except: curr_dom_final = 0



            if await browser.check_challenge(page):
                log.warning(f"[scrape_search_tab] Hit challenge on '{keyword}'")
                break
            
            if len(state.posts) >= max_posts:
                break
                
            no_new = no_new + 1 if len(state.posts) == prev_count and state.filtered_out == prev_filtered else 0
            if no_new >= 4 and curr_dom_final == prev_dom:
                if not recovery_attempted:
                    log.warning('[scrape_loop] Stalled >60s. Attempting recovery (dismiss, refresh)...')
                    await dismiss_instagram_modals(page)
                    await page.evaluate('window.scrollTo(0, 0)')
                    await asyncio.sleep(2)
                    try: await page.reload(timeout=30000)
                    except: pass
                    await browser.human_delay(3, 5)
                    recovery_attempted = True
                    no_new = 0
                    continue
                else:
                    break
                
    except Exception as exc:
        log.error(f"[scrape_search_tab] Error '{keyword}': {exc}")
    
    return _serialize_posts(state.posts)


# ═══════════════════════════════════════════════════════
#  Skill 5: master_viral_hunter
# ═══════════════════════════════════════════════════════

async def master_viral_hunter(
    seed_keyword: str,
    time_limit_hours: int = 24,
    top_n: int = 30,
    filters: Optional[dict] = None,
    include_deep_search: bool = False,
    do_explore: bool = True,
    explore_limit: int = 80,
    explore_scrolls: int = 20,
    do_feed: bool = True,
    feed_limit: int = 40,
    feed_scrolls: int = 15,
    fetch_images: bool = True,
    fetch_reels: bool = True,
    fetch_carousels: bool = True,
    min_posts_target: int = 10,
    max_scrolls: int = 60,
    progress_cb: Optional[Any] = None,
    stop_event: Optional[Any] = None
) -> dict[str, Any]:
    """
    Main orchestrator for the viral content hunting pipeline.
    """
    log.info(f"[master_viral_hunter] Seed: '{seed_keyword}', limit: {time_limit_hours}h, deep: {include_deep_search}")
    
    global_state = InterceptorState()
    current_status = "Инициализация..."

    def wrapped_cb(stats):
        if progress_cb:
            stats["status_text"] = current_status
            stats["liked"] = global_state.liked_count
            progress_cb(stats)

    # Build PostFilter — enforce time_limit and user-set criteria
    f_data = filters or {}
    min_likes_val = f_data.get("min_likes", 0)
    excl_zero = f_data.get("exclude_zero_engagement", False)
    only_ai = f_data.get("only_ai_topics", False)
    post_filter = PostFilter(
        min_likes=min_likes_val,
        exclude_zero_engagement=excl_zero,
        max_age_hours=time_limit_hours,
        only_ai_topics=only_ai
    )
    log.info(f"[master] PostFilter: min_likes={min_likes_val}, excl_zero={excl_zero}, max_age={time_limit_hours}h, only_ai={only_ai}")

    all_posts: list[dict] = []
    
    # Parse multiple keywords if provided
    kw_list = [k.strip() for k in seed_keyword.split(",") if k.strip()]
    if not kw_list:
        kw_list = [seed_keyword]

    # Step 1 — Expand keywords (Optional, riskier)
    if include_deep_search:
        log.info("[master] Step 1/4: Expanding search keywords...")
        # Expand based on the first keyword
        expanded = await expand_search_keywords(kw_list[0])
        # Combine provided list with expanded list uniquely
        keywords = list(dict.fromkeys(kw_list + expanded))
    else:
        log.info("[master] Step 1/4: Safe mode — skipping keyword expansion.")
        keywords = kw_list

    if do_feed:
        if stop_event and stop_event.is_set(): log.info("[master] Stop event set before Feed")
        else:
            log.info(f"[master] Step 2/4: Scraping home feed (Limit: {feed_limit})...")
            current_status = "Сканируем Ленту..."
            wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})
            try:
                feed_posts = await scrape_feed(time_limit_hours, max_posts=feed_limit, post_filter=post_filter, scrolls_limit=feed_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, progress_cb=wrapped_cb, stop_event=stop_event, global_state=global_state)
                log.info(f"[master] Feed returned {len(feed_posts)} posts")
                all_posts.extend(feed_posts)
            except Exception as exc:
                log.error(f"[master] Feed scrape failed: {exc}")
    else:
        log.info("[master] Step 2/4: Skipping home feed by user setting.")

    if do_explore:
        if stop_event and stop_event.is_set(): log.info("[master] Stop event set before Explore")
        else:
            log.info(f"[master] Step 3/4: Scraping explore (Limit: {explore_limit})...")
            current_status = "Сканируем Интересное..."
            wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})
            try:
                explore_posts = await scrape_explore(time_limit_hours, max_posts=explore_limit, post_filter=post_filter, scrolls_limit=explore_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, progress_cb=wrapped_cb, stop_event=stop_event, global_state=global_state)
                log.info(f"[master] Explore returned {len(explore_posts)} posts")
                all_posts.extend(explore_posts)
            except Exception as exc:
                log.error(f"[master] Explore scrape failed: {exc}")
    else:
        log.info("[master] Step 3/4: Skipping explore by user setting.")

    search_ai_bulk = f_data.get("search_ai_bulk", False)
    ai_bulk_threads = int(f_data.get("ai_bulk_threads", 3))
    ai_bulk_scrolls = int(f_data.get("ai_bulk_scrolls", 0))
    if search_ai_bulk:
        log.info(f"[master] Step 4/4: RUNNING BULK AI CONCURRENT SEARCH ({ai_bulk_threads} threads)...")
        from interceptor import AI_KEYWORDS
        AI_SEARCH_KEYWORDS = AI_KEYWORDS
        browser = StealthBrowser()
        await browser.launch(headless=False, hidden=True)
        sem = asyncio.Semaphore(ai_bulk_threads) # Dynamic concurrent tabs
        
        keywords_total = len(AI_SEARCH_KEYWORDS)
        keywords_done = 0
        current_status = f"Турбо-поиск: 0/{keywords_total}"
        wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})

        async def _worker(kw: str):
            nonlocal keywords_done, current_status
            
            kw_u = kw.upper()
            if ai_bulk_scrolls > 0:
                dyn_scrolls = ai_bulk_scrolls
            elif kw_u in ["CHATGPT", "GPT", "OPENAI", "CLAUDE", "OPUS", "SONNET", "HAIKU", "ANTHROPIC", "GEMINI"]:
                dyn_scrolls = 15
            elif kw_u in ["ELEVENLABS", "GROK"]:
                dyn_scrolls = 10
            else:
                dyn_scrolls = 5
                
            # Disable extra AI topic text filtering since the search kw itself guarantees it's an AI post
            local_filter = PostFilter(
                min_likes=post_filter.min_likes,
                exclude_zero_engagement=post_filter.exclude_zero_engagement,
                max_age_hours=post_filter.max_age_hours,
                only_ai_topics=False
            )
            
            async with sem:
                if stop_event and stop_event.is_set(): return []
                try:
                    page = await browser.new_stealth_tab()
                    results = await scrape_search_tab(
                        browser=browser, page=page, keyword=kw,
                        time_limit_hours=time_limit_hours, max_posts=50,
                        post_filter=local_filter, scrolls_limit=dyn_scrolls,
                        fetch_images=fetch_images, fetch_reels=fetch_reels,
                        fetch_carousels=fetch_carousels, progress_cb=wrapped_cb,
                        stop_event=stop_event, global_state=global_state
                    )
                    await page.close()
                    keywords_done += 1
                    current_status = f"Турбо-поиск: {keywords_done}/{keywords_total}"
                    wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})
                    
                    return results
                except Exception as e:
                    log.error(f"[master_worker] {kw} failed: {e}")
                    return []
                    
        tasks = [_worker(kw) for kw in AI_SEARCH_KEYWORDS]
        all_res = await asyncio.gather(*tasks)
        for r in all_res:
            all_posts.extend(r)
            
        await browser.rescue_window()
        await browser.close()

    else:
        # Step 4 — standard Search keywords
        log.info("[master] Step 4/4: Scraping standard keywords/search...")
        if include_deep_search:
            # Visit multiple related targets (up to 5 to avoid block)
            total_std = len(keywords[:5])
            for i, kw in enumerate(keywords[:5], 1):
                if stop_event and stop_event.is_set():
                    log.info(f"[master] Stop event set before keyword {kw}")
                    break
                current_status = f"Поиск: {i}/{total_std}"
                wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})
                try:
                    all_posts.extend(await scrape_search(kw, time_limit_hours, max_posts=50, post_filter=post_filter, scrolls_limit=max_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, progress_cb=wrapped_cb, stop_event=stop_event, global_state=global_state))
                except Exception as exc:
                    log.error(f"[master] Search '{kw}' failed: {exc}")
                await asyncio.sleep(random.uniform(2, 4))
        else:
            # Safe mode: Iterate exactly over the provided keywords
            total_std = len(keywords)
            for i, kw in enumerate(keywords, 1):
                if stop_event and stop_event.is_set():
                    log.info(f"[master] Stop event set before keyword {kw}")
                    break
                current_status = f"Поиск: {i}/{total_std}"
                wrapped_cb({"collected": len(global_state.posts), "filtered": global_state.filtered_out, "reels": global_state.reels_count, "carousels": global_state.carousels_count, "photos": global_state.photos_count})
                try:
                    all_posts.extend(await scrape_search(kw, time_limit_hours, max_posts=50, post_filter=post_filter, scrolls_limit=max_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, progress_cb=wrapped_cb, stop_event=stop_event, global_state=global_state))
                except Exception as exc:
                    log.error(f"[master] Search '{kw}' failed: {exc}")
                await asyncio.sleep(random.uniform(2, 4))

    # Deduplicate
    seen: set[str] = set()
    unique: list[dict] = []
    for p in all_posts:
        pid = p.get("post_id", "")
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(p)

    unique.sort(key=lambda x: x.get("velocity_score", 0), reverse=True)
    top_posts = unique[:top_n]

    # Save
    results_path = OUTPUT_DIR / "viral_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(top_posts, f, ensure_ascii=False, indent=2)

    html_path = OUTPUT_DIR / "results.html"
    generate_results_html(top_posts, str(html_path))

    summary = {
        "total_collected": len(unique),
        "top_posts_count": len(top_posts),
        "keywords_used": keywords,
        "results_json": str(results_path),
        "results_html": str(html_path),
        "top_posts": top_posts,
    }
    log.info(f"[master_viral_hunter] Complete — {len(unique)} unique, top {len(top_posts)}")
    return summary
