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
        page = await browser.launch(headless=False)
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
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True
) -> list[dict]:
    log.info(f"[scrape_feed] Starting (limit: {time_limit_hours}h)")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source="feed", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter)
        ))
        await safe_goto(page, "https://www.instagram.com/")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = scrolls_limit, 0
        DOM_SEL = "article, a[href*='/p/']"
        for i in range(max_scrolls):
            prev_count = len(state.posts)
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

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
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom:
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

            # ── Occasional human post-open simulation ──
            if batch_loaded and random.random() < 0.4:
                try:
                    posts_loc = await page.locator(DOM_SEL).all()
                    if posts_loc:
                        pool = posts_loc[-10:]
                        posts_to_open = random.sample(pool, min(len(pool), random.randint(1, 3)))
                        for p_el in posts_to_open:
                            log.debug("[Human] Opening random post from Feed...")
                            await p_el.click()
                            await browser.human_delay(2, 5)
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(1)
                except Exception:
                    pass

            if random.random() < 0.3:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break

            if len(state.posts) >= max_posts:
                log.info(f"[scrape_feed] Reached max_posts ({max_posts}), stopping.")
                break

            no_new = no_new + 1 if len(state.posts) == prev_count else 0
            if no_new >= 8 and curr_dom_final == prev_dom:
                log.warning(f"[scrape_feed] 8 consecutive scrolls with no new content. Stopping.")
                break
            if (i + 1) % 20 == 0:
                _save_progress(state.posts, "feed")
    except Exception as exc:
        log.error(f"[scrape_feed] Error: {exc}")
        _save_progress(state.posts, "feed_error")
    finally:
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
    fetch_images: bool = True, fetch_reels: bool = True, fetch_carousels: bool = True
) -> list[dict]:
    log.info(f"[scrape_explore] Starting (limit: {time_limit_hours}h)")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source="explore", fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels, post_filter=post_filter)
        ))
        await safe_goto(page, "https://www.instagram.com/explore/")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = scrolls_limit, 0
        DOM_SEL = "a[href*='/p/'], a[href*='/reel/']"
        for i in range(max_scrolls):
            prev_count = len(state.posts)
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

            # ── True bottom scroll — triggers IG's infinite-scroll loader ──
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.8, 1.4))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            log.debug(f"[explore] scroll {i+1}/{max_scrolls} — DOM before: {prev_dom}, API posts: {prev_count}")

            # ── Wait up to 20s for new DOM nodes OR new API interceptions ──
            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 20:
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom:
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

            if batch_loaded and random.random() < 0.4:
                try:
                    posts_loc = await page.locator(DOM_SEL).all()
                    if posts_loc:
                        pool = posts_loc[-10:]
                        posts_to_open = random.sample(pool, min(len(pool), random.randint(1, 3)))
                        for p_el in posts_to_open:
                            log.debug("[Human] Opening random post from Explore...")
                            await p_el.click()
                            await browser.human_delay(2, 5)
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(1)
                except Exception:
                    pass

            if random.random() < 0.25:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break

            if len(state.posts) >= max_posts:
                log.info(f"[scrape_explore] Reached max_posts ({max_posts}), stopping.")
                break

            no_new = no_new + 1 if len(state.posts) == prev_count else 0
            if no_new >= 8 and curr_dom_final == prev_dom:
                log.warning(f"[scrape_explore] 8 consecutive scrolls with no new content. Stopping.")
                break
            if (i + 1) % 15 == 0:
                _save_progress(state.posts, "explore")
    except Exception as exc:
        log.error(f"[scrape_explore] Error: {exc}")
        _save_progress(state.posts, "explore_error")
    finally:
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
) -> list[dict]:
    log.info(f"[scrape_search] Keyword: '{keyword}' (limit: {time_limit_hours}h, max: {max_posts})")
    browser = StealthBrowser()
    state = InterceptorState()
    try:
        page = await browser.launch(headless=False)
        page.on("response", lambda r: asyncio.ensure_future(
            handle_response(r, state, source=f"search:{keyword}", post_filter=post_filter)
        ))
        clean_keyword = keyword.lstrip("#").strip()
        # New Global Search URL
        await safe_goto(page, f"https://www.instagram.com/explore/search/keyword/?q={clean_keyword}")
        await browser.human_delay(3, 5)

        max_scrolls, no_new = 40, 0
        DOM_SEL = "a[href*='/p/'], a[href*='/reel/']"
        for i in range(max_scrolls):
            prev_count = len(state.posts)
            try:
                prev_dom = await page.locator(DOM_SEL).count()
            except Exception:
                prev_dom = 0

            # ── Scroll to true bottom so IG's sentinel enters viewport ──
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.8, 1.4))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            log.debug(f"[search:{keyword}] scroll {i+1}/{max_scrolls} — DOM before: {prev_dom}, API posts: {prev_count}")

            # ── Wait up to 20s for new DOM nodes OR new API interceptions ──
            batch_loaded = False
            wait_start = time.time()
            while time.time() - wait_start < 20:
                await asyncio.sleep(0.8)
                try:
                    curr_dom = await page.locator(DOM_SEL).count()
                except Exception:
                    curr_dom = prev_dom
                if len(state.posts) > prev_count or curr_dom > prev_dom:
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

            if batch_loaded and random.random() < 0.4:
                try:
                    posts_loc = await page.locator(DOM_SEL).all()
                    if posts_loc:
                        pool = posts_loc[-10:]
                        posts_to_open = random.sample(pool, min(len(pool), random.randint(1, 3)))
                        for p_el in posts_to_open:
                            log.debug(f"[Human] Opening random search post for '{keyword}'...")
                            await p_el.click()
                            await browser.human_delay(2, 5)
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(1)
                except Exception:
                    pass

            if random.random() < 0.2:
                await browser.human_move_mouse(page)
            if await browser.check_challenge(page):
                log.warning("[scrape_search] Hit captcha/challenge, breaking loop.")
                await browser.handle_challenge([asdict(p) for p in state.posts])
                break
            if len(state.posts) >= max_posts:
                log.info(f"[scrape_search] Reached max_posts ({max_posts}), stopping.")
                break
            
            no_new = no_new + 1 if len(state.posts) == prev_count else 0
            if no_new >= 6 and curr_dom_final == prev_dom:
                log.warning(f"[scrape_search] 6 scrolls with no new posts. Stopping.")
                break
            log.debug(f"[search:{keyword}] no_new={no_new}, posts={len(state.posts)}")
    except Exception as exc:
        log.error(f"[scrape_search] Error: {exc}")
        _save_progress(state.posts, f"search_{clean_keyword}_error")
    finally:
        await browser.close()

    log.info(f"[scrape_search] Done — {len(state.posts)} posts for '{keyword}'")
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
    do_feed: bool = True,
    feed_limit: int = 40,
    fetch_images: bool = True,
    fetch_reels: bool = True,
    fetch_carousels: bool = True,
    min_posts_target: int = 10,
    max_scrolls: int = 60
) -> dict[str, Any]:
    """
    Main orchestrator for the viral content hunting pipeline.
    """
    log.info(f"[master_viral_hunter] Seed: '{seed_keyword}', limit: {time_limit_hours}h, deep: {include_deep_search}")
    
    # Build PostFilter — enforce time_limit and user-set criteria
    f_data = filters or {}
    min_likes_val = f_data.get("min_likes", 0)
    excl_zero = f_data.get("exclude_zero_engagement", False)
    post_filter = PostFilter(
        min_likes=min_likes_val,
        exclude_zero_engagement=excl_zero,
        max_age_hours=time_limit_hours,
    )
    log.info(f"[master] PostFilter: min_likes={min_likes_val}, excl_zero={excl_zero}, max_age={time_limit_hours}h")

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

    # Step 2 — Feed
    if do_feed:
        log.info(f"[master] Step 2/4: Scraping home feed (Limit: {feed_limit})...")
        try:
            feed_posts = await scrape_feed(time_limit_hours, max_posts=feed_limit, post_filter=post_filter, scrolls_limit=max_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels)
            log.info(f"[master] Feed returned {len(feed_posts)} posts")
            all_posts.extend(feed_posts)
        except Exception as exc:
            log.error(f"[master] Feed scrape failed: {exc}")
    else:
        log.info("[master] Step 2/4: Skipping home feed by user setting.")

    # Step 3 — Explore
    if do_explore:
        log.info(f"[master] Step 3/4: Scraping explore (Limit: {explore_limit})...")
        try:
            explore_posts = await scrape_explore(time_limit_hours, max_posts=explore_limit, post_filter=post_filter, scrolls_limit=max_scrolls, fetch_images=fetch_images, fetch_reels=fetch_reels, fetch_carousels=fetch_carousels)
            log.info(f"[master] Explore returned {len(explore_posts)} posts")
            all_posts.extend(explore_posts)
        except Exception as exc:
            log.error(f"[master] Explore scrape failed: {exc}")
    else:
        log.info("[master] Step 3/4: Skipping explore by user setting.")

    # Step 4 — Search keywords
    log.info("[master] Step 4/4: Scraping keywords/search...")
    if include_deep_search:
        # Visit multiple related targets (up to 5 to avoid block)
        for kw in keywords[:5]:
            try:
                all_posts.extend(await scrape_search(kw, time_limit_hours, max_posts=50, post_filter=post_filter))
            except Exception as exc:
                log.error(f"[master] Search '{kw}' failed: {exc}")
            await asyncio.sleep(random.uniform(3, 7))
    else:
        # Safe mode: Iterate exactly over the provided keywords
        for kw in keywords:
            try:
                all_posts.extend(await scrape_search(kw, time_limit_hours, max_posts=50, post_filter=post_filter))
            except Exception as exc:
                log.error(f"[master] Search '{kw}' failed: {exc}")
            await asyncio.sleep(random.uniform(3, 7))

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
