"""
mcp_server.py — MCP entry point for Claude Desktop (stdio transport).

Exposes 5 tools with Pydantic-validated parameters including
server-side post filters (min/max likes, followers, etc.)
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Fix CWD to project root (Claude Desktop may launch from system32)
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import BaseModel, Field
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import skills
from interceptor import PostFilter

# ── Logging (file only — stdout is reserved for MCP JSON-RPC) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("mcp_server")


# ── Pydantic parameter models ──────────────────────────

class FilterMixin(BaseModel):
    """Common filter fields shared across scraping tools."""
    min_likes: int = Field(default=0, ge=0, description="Минимум лайков (0 = без ограничения)")
    max_likes: int = Field(default=0, ge=0, description="Максимум лайков (0 = без ограничения). Исключает миллионники.")
    min_comments: int = Field(default=0, ge=0, description="Минимум комментариев")
    max_comments: int = Field(default=0, ge=0, description="Максимум комментариев (0 = без ограничения)")
    max_followers: int = Field(default=0, ge=0, description="Максимум подписчиков автора (0 = без лимита). 100000 = исключить миллионников")
    min_followers: int = Field(default=0, ge=0, description="Минимум подписчиков автора")
    exclude_zero_engagement: bool = Field(default=False, description="Исключить посты с 0 лайков И 0 комментов")

    def to_post_filter(self) -> Optional[PostFilter]:
        f = PostFilter(
            min_likes=self.min_likes, max_likes=self.max_likes,
            min_comments=self.min_comments, max_comments=self.max_comments,
            max_followers=self.max_followers, min_followers=self.min_followers,
            exclude_zero_engagement=self.exclude_zero_engagement,
        )
        if (f.min_likes == 0 and f.max_likes == 0 and f.min_comments == 0
                and f.max_comments == 0 and f.max_followers == 0
                and f.min_followers == 0 and not f.exclude_zero_engagement):
            return None
        return f


class ExpandKeywordsParams(BaseModel):
    seed_keyword: str = Field(description="Seed word to expand via Instagram autocomplete")


class ScrapeFeedParams(FilterMixin):
    time_limit_hours: int = Field(default=24, ge=1, le=168, description="Только посты моложе N часов")


class ScrapeExploreParams(FilterMixin):
    time_limit_hours: int = Field(default=24, ge=1, le=168, description="Только посты моложе N часов")


class ScrapeSearchParams(FilterMixin):
    keyword: str = Field(description="Ключевое слово или хештег")
    time_limit_hours: int = Field(default=24, ge=1, le=168, description="Только посты моложе N часов")
    max_posts: int = Field(default=100, ge=1, le=500, description="Максимум постов для сбора")


class MasterViralHunterParams(FilterMixin):
    seed_keyword: str = Field(description="Ключевое слово для поиска вирального контента")
    time_limit_hours: int = Field(default=24, ge=1, le=168, description="Только посты моложе N часов")


class LaunchGuiParams(BaseModel):
    """No parameters needed — just opens the window."""


# ── MCP Server ─────────────────────────────────────────

app = Server("instagram-stealth-scraper")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="expand_search_keywords",
            description=(
                "Эмулирует ввод ключевого слова в поиск Instagram и перехватывает "
                "подсказки автодополнения. Возвращает 10-15 связанных тем."
            ),
            inputSchema=ExpandKeywordsParams.model_json_schema(),
        ),
        Tool(
            name="scrape_feed",
            description=(
                "Скроллит домашнюю ленту Instagram, перехватывая Reels и Карусели "
                "из сетевого трафика. Поддерживает фильтры по лайкам/подписчикам."
            ),
            inputSchema=ScrapeFeedParams.model_json_schema(),
        ),
        Tool(
            name="scrape_explore",
            description=(
                "Скроллит вкладку Интересное (Explore). Перехватывает Reels и Карусели. "
                "Поддерживает фильтры."
            ),
            inputSchema=ScrapeExploreParams.model_json_schema(),
        ),
        Tool(
            name="scrape_search",
            description=(
                "Открывает страницу хештега и скроллит. Собирает все типы постов. "
                "Поддерживает фильтры по метрикам и подписчикам."
            ),
            inputSchema=ScrapeSearchParams.model_json_schema(),
        ),
        Tool(
            name="master_viral_hunter",
            description=(
                "🎯 МАСТЕР-СКИЛЛ: Расширяет ключевое слово через автодополнение, "
                "затем парсит Ленту, Интересное и до 5 хештегов. Ранжирует по "
                "Индексу Виральности и генерирует HTML-отчёт с CSV/Google Sheets экспортом. "
                "Поддерживает все фильтры: мин/макс лайков, исключение миллионников, "
                "исключение нулевого вовлечения."
            ),
            inputSchema=MasterViralHunterParams.model_json_schema(),
        ),
        Tool(
            name="launch_gui",
            description=(
                "🖥️ Запускает главное окно Banana Parser с графическим интерфейсом. "
                "Открывает нативное десктопное окно где пользователь может настроить "
                "параметры парсинга, запустить сбор и увидеть дашборд с результатами. "
                "Вызывается без параметров."
            ),
            inputSchema=LaunchGuiParams.model_json_schema(),
        ),
        Tool(
            name="launch_auth_window",
            description=(
                "🔑 Открывает окно авторизации Instagram Playwright для ручного входа. "
                "Использовать, если storage_state.json отсутствует или сессия истекла."
            ),
            inputSchema=LaunchGuiParams.model_json_schema(),
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info(f"Tool called: {name} with args: {arguments}")

    try:
        if name == "expand_search_keywords":
            params = ExpandKeywordsParams(**arguments)
            result = await skills.expand_search_keywords(params.seed_keyword)
            return [TextContent(
                type="text",
                text=json.dumps({"suggestions": result}, ensure_ascii=False, indent=2),
            )]

        elif name == "scrape_feed":
            params = ScrapeFeedParams(**arguments)
            result = await skills.scrape_feed(params.time_limit_hours, params.to_post_filter())
            return [TextContent(
                type="text",
                text=json.dumps({
                    "posts_count": len(result),
                    "posts": result[:50],
                }, ensure_ascii=False, indent=2),
            )]

        elif name == "scrape_explore":
            params = ScrapeExploreParams(**arguments)
            result = await skills.scrape_explore(params.time_limit_hours, params.to_post_filter())
            return [TextContent(
                type="text",
                text=json.dumps({
                    "posts_count": len(result),
                    "posts": result[:50],
                }, ensure_ascii=False, indent=2),
            )]

        elif name == "scrape_search":
            params = ScrapeSearchParams(**arguments)
            result = await skills.scrape_search(
                params.keyword, params.time_limit_hours, params.max_posts,
                params.to_post_filter(),
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "keyword": params.keyword,
                    "posts_count": len(result),
                    "posts": result[:50],
                }, ensure_ascii=False, indent=2),
            )]

        elif name == "master_viral_hunter":
            params = MasterViralHunterParams(**arguments)
            result = await skills.master_viral_hunter(
                params.seed_keyword, params.time_limit_hours,
                post_filter=params.to_post_filter(),
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "total_collected": result["total_collected"],
                    "top_posts_count": result["top_posts_count"],
                    "keywords_used": result["keywords_used"],
                    "results_html": result["results_html"],
                    "results_json": result["results_json"],
                    "top_5_preview": result["top_posts"][:5],
                }, ensure_ascii=False, indent=2),
            )]

        elif name == "launch_gui":
            import subprocess
            import sys
            import platform

            # Open standard parser window
            cmd_prefix = ["cmd", "/c", "start"] if platform.system() == "Windows" else ["osascript", "-e", 'tell app "Terminal" to do script "python run_scraper.py"']
            if platform.system() == "Windows":
                subprocess.Popen(cmd_prefix + [sys.executable, "run_scraper.py"])
            else:
                subprocess.Popen(cmd_prefix)

            return [TextContent(
                type="text",
                text="Графическое окно парсера успешно запущено в отдельном процессе.",
            )]
            
        elif name == "launch_auth_window":
            import subprocess
            import sys
            import platform

            # Open authentication window
            cmd_prefix = ["cmd", "/c", "start"] if platform.system() == "Windows" else ["osascript", "-e", 'tell app "Terminal" to do script "python auth.py"']
            if platform.system() == "Windows":
                subprocess.Popen(cmd_prefix + [sys.executable, "auth.py"])
            else:
                subprocess.Popen(cmd_prefix)

            return [TextContent(
                type="text",
                text="Окно авторизации Instagram успешно запущено. Подождите пока пользователь залогинится.",
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as exc:
        log.error(f"Tool {name} failed: {exc}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(exc)}, ensure_ascii=False),
        )]


async def main() -> None:
    log.info("Starting Instagram Stealth Scraper MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
