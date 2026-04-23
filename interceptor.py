"""
interceptor.py — Passive network interception layer.

Subscribes to page.on('response') events and extracts Instagram
post data from background GraphQL / JSON responses on the fly.
Uses defensive programming (.get()) to handle Instagram's
ever-changing response shapes.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger(__name__)

@dataclass
class PostFilter:
    """Server-side filter criteria applied during collection."""
    min_likes: int = 0
    max_likes: int = 0          # 0 = no upper limit
    min_comments: int = 0
    max_comments: int = 0       # 0 = no upper limit
    min_views: int = 0
    max_views: int = 0          # 0 = no upper limit
    max_followers: int = 0      # 0 = no upper limit (exclude millionaires)
    min_followers: int = 0
    max_age_hours: Optional[int] = None
    exclude_zero_engagement: bool = False  # skip posts with 0 likes AND 0 comments
    filter_keywords: list[str] = field(default_factory=list)
    only_ru_en: bool = False
    # AI semantic classifier fields (optional, requires sentence-transformers)
    ai_topic_text: str = ""      # free-text topic description for semantic matching
    ai_enabled: bool = False     # toggle: True = use AI when keyword match fails
    ai_threshold: float = 0.35   # cosine similarity threshold (0.0–1.0)

    def matches(self, post: "PostData") -> bool:
        """Return True if the post passes all filter criteria."""
        # Date filter (Strict)
        if self.max_age_hours is not None and post.timestamp > 0:
            current_time = int(time.time())
            age_hours = (current_time - post.timestamp) / 3600
            if age_hours > self.max_age_hours:
                return False

        if self.exclude_zero_engagement and post.likes == 0 and post.comments == 0:
            return False
        if self.min_likes > 0 and post.likes < self.min_likes:
            return False
        if self.max_likes > 0 and post.likes > self.max_likes:
            return False
        if self.min_comments > 0 and post.comments < self.min_comments:
            return False
        if self.max_comments > 0 and post.comments > self.max_comments:
            return False
        if self.min_views > 0 and post.views < self.min_views:
            return False
        if self.max_views > 0 and post.views > self.max_views:
            return False
        if self.max_followers > 0 and post.owner_followers > self.max_followers:
            return False
        if self.min_followers > 0 and post.owner_followers < self.min_followers:
            return False
            
        # Keyword / AI filter
        if self.filter_keywords:
            caption = post.caption_text or ""
            alt = getattr(post, 'alt_text', '') or ""
            subs = getattr(post, 'subtitles_text', '') or ""
            subs_uri = getattr(post, 'subtitles_uri', '') or ""
            all_text = (caption + " " + alt + " " + subs).lower()

            # Strip emojis, punctuation, urls — count only real words
            meaningful = re.sub(r'#\w+|@\w+|https?://\S+|[^\w\sа-яА-ЯёЁa-zA-Z]', '', all_text).strip()

            if not meaningful:
                # No text signal at all.
                # If there's a subtitles_uri we can fetch later → defer (pending).
                if subs_uri:
                    return None  # add_post() will queue for subtitle fetch
                elif post.is_reel or getattr(post, 'post_type', '') in ('reel', 'video'):
                    pass  # Reel without text → pass through (Instagram already filtered feed)
                else:
                    return None  # non-video with no text → defer/discard
            else:
                # Check if any keyword matches
                kw_match = any(kw.lower() in all_text for kw in self.filter_keywords if kw.strip())

                if not kw_match:
                    # Try AI semantic classifier as fallback
                    if self.ai_enabled and self.ai_topic_text:
                        try:
                            from ai_classifier import classifier as _clf
                            if _clf and _clf.is_ready():
                                score = _clf.score(meaningful)
                                if score < self.ai_threshold:
                                    return False
                            else:
                                return False  # AI enabled but not ready → strict
                        except Exception:
                            return False
                    else:
                        return False  # No keyword match, AI disabled → reject

        # Advanced Language detection filter (RU/EN precision)
        if self.only_ru_en and getattr(post, 'caption_text', ''):
            # Fast-path for Russian/Cyrillic
            if re.search(r'[а-яА-ЯёЁ]', post.caption_text):
                pass
            else:
                try:
                    # Clean the text of hashtags, mentions, and URLs which confuse the detector
                    clean_text = re.sub(r'#[\w_]+|@[\w_]+|https?://\S+', '', post.caption_text)
                    clean_text = re.sub(r'[^\w\s]', '', clean_text).strip()
                    
                    if len(clean_text) > 15:
                        from langdetect import detect
                        lang = detect(clean_text)
                        
                        # Blacklist the most common spam regions in AI niches to avoid false-rejecting English
                        banned_langs = {'hi', 'ar', 'id', 'es', 'pt', 'tr', 'fa', 'ur', 'th', 'vi', 'bn', 'ta', 'te', 'mr', 'ja', 'zh-cn', 'zh-tw', 'ko'}
                        if lang in banned_langs:
                            return False
                except Exception:
                    pass

            
        return True


@dataclass
class PostData:
    """Normalised representation of an Instagram post."""
    post_id: str = ""
    shortcode: str = ""
    post_type: str = "unknown"
    owner_username: str = ""
    owner_full_name: str = ""
    owner_followers: int = 0
    caption_text: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    timestamp: int = 0
    url: str = ""
    thumbnail_url: str = ""
    alt_text: str = ""          # Instagram auto-generated accessibility description
    subtitles_text: str = ""   # Reels subtitles / transcript
    subtitles_uri: str = ""    # CDN URI to fetch subtitles from (resolved later by batch fetcher)
    is_reel: bool = False
    is_carousel: bool = False
    carousel_count: int = 0
    source: str = ""


@dataclass
class InterceptorState:
    """Accumulates captured posts across multiple scrolls."""
    posts: list[PostData] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    response_count: int = 0
    error_count: int = 0
    oldest_timestamp: int = 0
    filtered_out: int = 0
    reels_count: int = 0
    liked_count: int = 0
    carousels_count: int = 0
    photos_count: int = 0
    pending: list = field(default_factory=list)  # reels deferred for subtitle check

    def add_post(self, post: PostData, post_filter: Optional[PostFilter] = None) -> bool:
        """Add a post if not already seen and passes filters."""
        if post.post_id in self.seen_ids or not post.post_id:
            return False
        if post_filter:
            result = post_filter.matches(post)
            if result is None:
                # Deferred: no text signal — queue for subtitle fetch
                if post.post_id not in self.seen_ids:
                    self.pending.append(post)
                    self.seen_ids.add(post.post_id)
                return False
            if not result:
                self.filtered_out += 1
                return False
        self.seen_ids.add(post.post_id)
        self.posts.append(post)
        if post.is_reel:
            self.reels_count += 1
        elif post.is_carousel:
            self.carousels_count += 1
        else:
            self.photos_count += 1
        if post.timestamp > 0:
            if self.oldest_timestamp == 0:
                self.oldest_timestamp = post.timestamp
            else:
                self.oldest_timestamp = min(self.oldest_timestamp, post.timestamp)
        return True


# ── GraphQL response patterns we intercept ───────────

GRAPHQL_PATTERNS = [
    "graphql/query",
    "api/v1/feed/timeline",
    "api/v1/feed/reels_tray",
    "api/v1/discover/web/explore_grid",
    "api/v1/tags/",
    "api/v1/feed/tag/",
    "web_search_typeahead",
    "web/search/topsearch",
    "api/v1/clips/",
    "api/v1/fbsearch/",
    "api/v1/users/search/"
]


def _matches_ig_api(url: str) -> bool:
    return any(pat in url for pat in GRAPHQL_PATTERNS)


def _detect_post_type(node: dict) -> str:
    media_type = node.get("media_type")
    product_type = node.get("product_type", "")
    typename = node.get("__typename", "")
    # Reels detection: clips product type, reel media flag, XDTGraphVideo/Reel, or clips_metadata
    if (product_type == "clips" or node.get("is_reel_media")
            or typename in ("XDTGraphVideo", "XDTGraphReel")
            or node.get("clips_metadata") is not None):
        return "reel"
    if typename in ("GraphSidecar", "XDTGraphSidecar") or node.get("carousel_media_count", 0) > 0:
        return "carousel"
    if media_type == 8:
        return "carousel"
    if media_type == 2:
        # media_type=2 is always video — all short-form vertical video is a Reel.
        # Some nodes lack product_type='clips' but are still Reels (Search API quirk).
        # Check for any Reel-specific signals first, then default to reel.
        if node.get("carousel_media_count", 0) > 0 or typename in ("GraphSidecar", "XDTGraphSidecar"):
            return "carousel"  # rare: carousels with video cover
        return "reel"  # media_type=2 → video → treat as Reel by default
    if media_type == 1:
        return "image"
    if typename == "GraphVideo" or node.get("is_video"):
        return "reel"  # GraphVideo in timeline feed is always a Reel
    # Fallback: if node has play_count/video_duration it's a video/Reel
    if node.get("play_count") or node.get("video_view_count") or node.get("video_duration"):
        return "reel"
    return "image"


def _safe_int(val: Any) -> int:
    if val is None:
        return 0
    try:
        v = int(val)
        return max(v, 0)
    except (ValueError, TypeError):
        return 0


def _extract_post(node: dict, source: str = "") -> Optional[PostData]:
    """Extract PostData from a single GraphQL media node."""
    try:
        post_id = str(node.get("pk", node.get("id", "")))
        shortcode = node.get("code", node.get("shortcode", ""))
        if not post_id and not shortcode:
            return None

        post_type = _detect_post_type(node)

        owner = node.get("owner", node.get("user", {})) or {}
        username = owner.get("username", "")
        full_name = owner.get("full_name", "")
        owner_followers = _safe_int(
            owner.get("follower_count")
            or owner.get("edge_followed_by", {}).get("count")
        )

        caption = ""
        cap_obj = node.get("caption")
        if isinstance(cap_obj, dict):
            caption = cap_obj.get("text", "")
        elif isinstance(cap_obj, str):
            caption = cap_obj
        if not caption:
            edges = node.get("edge_media_to_caption", {}).get("edges", [])
            if edges:
                caption = edges[0].get("node", {}).get("text", "")

        likes = _safe_int(
            node.get("like_count")
            or node.get("edge_media_preview_like", {}).get("count")
            or node.get("edge_liked_by", {}).get("count")
        )
        comments = _safe_int(
            node.get("comment_count")
            or node.get("edge_media_to_comment", {}).get("count")
            or node.get("edge_media_preview_comment", {}).get("count")
        )
        views = _safe_int(
            node.get("play_count")
            or node.get("video_view_count")
            or node.get("view_count")
        )
        timestamp = _safe_int(
            node.get("taken_at")
            or node.get("taken_at_timestamp")
            or node.get("device_timestamp")
        )

        url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""
        if post_type == "reel" and shortcode:
            url = f"https://www.instagram.com/reel/{shortcode}/"

        thumb = (
            node.get("thumbnail_src")
            or node.get("display_url")
            or node.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
            if isinstance(node.get("image_versions2"), dict) else ""
        )
        if not thumb:
            thumb = node.get("display_url", "")

        is_reel = post_type in ("reel", "video")
        is_carousel = post_type == "carousel"
        carousel_count = _safe_int(
            node.get("carousel_media_count")
            or len(node.get("edge_sidecar_to_children", {}).get("edges", []))
            or len(node.get("carousel_media", []))
        )

        # Extract Instagram auto-generated accessibility text (image AI description)
        alt_text = ""
        acc = node.get("accessibility_caption", "")
        if acc and isinstance(acc, str):
            alt_text = acc[:300]

        # Extract Reels subtitles / transcript text and CDN URI for batch fetching
        subtitles_text = ""
        subtitles_uri = ""
        subs_raw = node.get("video_subtitles", [])
        if isinstance(subs_raw, list) and subs_raw:
            # Inline subtitles: list of {text: ...} dicts
            parts = [s.get("text", s.get("content", "")) for s in subs_raw if isinstance(s, dict)]
            subtitles_text = " ".join(filter(None, parts))[:400]
        elif isinstance(subs_raw, dict):
            # URI form: {uri: "https://cdn..."}
            subtitles_uri = subs_raw.get("uri", subs_raw.get("url", ""))
        # Also check top-level video_subtitles_uri field
        if not subtitles_uri:
            subtitles_uri = str(node.get("video_subtitles_uri", "") or node.get("subtitles_uri", "") or "")

        return PostData(
            post_id=post_id, shortcode=shortcode, post_type=post_type,
            owner_username=username, owner_full_name=full_name,
            owner_followers=owner_followers,
            caption_text=caption[:500], likes=likes, comments=comments,
            views=views, timestamp=timestamp, url=url,
            thumbnail_url=thumb if isinstance(thumb, str) else "",
            is_reel=is_reel, is_carousel=is_carousel,
            carousel_count=carousel_count, source=source,
            alt_text=alt_text, subtitles_text=subtitles_text, subtitles_uri=subtitles_uri,
        )
    except Exception as exc:
        log.debug(f"Failed to extract post node: {exc}")
        return None


def _find_media_nodes(obj: Any, depth: int = 0, max_depth: int = 12) -> list[dict]:
    if depth > max_depth:
        return []
    results: list[dict] = []
    if isinstance(obj, dict):
        has_code = "shortcode" in obj or "code" in obj
        has_id = "pk" in obj or "id" in obj
        has_media = "media_type" in obj or "__typename" in obj or "taken_at" in obj or "taken_at_timestamp" in obj
        if has_code and has_id and has_media:
            results.append(obj)
        for v in obj.values():
            results.extend(_find_media_nodes(v, depth + 1, max_depth))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_find_media_nodes(item, depth + 1, max_depth))
    return results


def extract_search_suggestions(data: dict) -> list[str]:
    suggestions: list[str] = []
    for ht in data.get("hashtags", []):
        name = ht.get("hashtag", {}).get("name", "")
        if name:
            suggestions.append(f"#{name}")
    for u in data.get("users", []):
        uname = u.get("user", u).get("username", "")
        if uname:
            suggestions.append(f"@{uname}")
    for p in data.get("places", []):
        title = p.get("place", p).get("title", "")
        if title:
            suggestions.append(title)
    return suggestions


async def handle_response(
    response,
    state: InterceptorState,
    source: str = "",
    fetch_images: bool = True,
    fetch_reels: bool = True,
    fetch_carousels: bool = True,
    post_filter: Optional[PostFilter] = None,
    progress_cb: Optional[Any] = None,
    global_state: Optional[InterceptorState] = None,
) -> None:
    """Callback for page.on('response'). Parses JSON and extracts posts."""
    url = response.url
    if not _matches_ig_api(url):
        return
    state.response_count += 1
    try:
        body = await response.body()
        text = body.decode("utf-8", errors="replace")
        if text.startswith("for (;;);"):
            text = text[len("for (;;);"):]
        data = json.loads(text)
    except Exception:
        state.error_count += 1
        return

    nodes = _find_media_nodes(data)
    added = 0
    for node in nodes:
        post = _extract_post(node, source=source)
        if post is None:
            continue
        if not fetch_images and post.post_type in ("image", "unknown", ""):
            continue
        if not fetch_reels and post.post_type in ("reel", "video"):
            continue
        if not fetch_carousels and post.post_type == "carousel":
            continue
        added_local = state.add_post(post, post_filter=post_filter)
        if global_state:
            global_state.add_post(post, post_filter=post_filter)
            
        if added_local:
            added += 1

    if added > 0 or len(nodes) > 0:
        log.info(f"[{source}] Found {len(nodes)} posts -> Added {added} (Total collected: {len(state.posts)}, Filtered out: {state.filtered_out}) from api endpoint")
        if progress_cb:
            cb_state = global_state if global_state else state
            try:
                progress_cb({
                    "collected": len(cb_state.posts),
                    "filtered": cb_state.filtered_out,
                    "reels": cb_state.reels_count,
                    "carousels": cb_state.carousels_count,
                    "photos": cb_state.photos_count
                })
            except Exception as e:
                log.debug(f"progress_cb error: {e}")
