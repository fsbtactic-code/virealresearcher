# Banana Parser — Claude Code Instructions

## Slash Commands

- `/banana-install` — Установить всё: зависимости, Playwright, проверить готовность
- `/banana-launch` — Запустить главное окно парсера

## What is this?

Banana Parser — Instagram stealth scraper. Десктопное приложение (pywebview + Playwright) для поиска вирусного контента конкурентов.

## Quick Setup

```bash
python install_all.py    # установка всего
python auth.py           # авторизация Instagram (один раз)
python run_scraper.py    # запуск GUI
```

## If something breaks

1. Read `.ai-context.md` for architecture and known issues
2. Common fixes:
   - `storage_state.json not found` → run `python auth.py`
   - `playwright` errors → run `python -m playwright install chromium`
   - Import errors → run `pip install -r requirements.txt`
   - Window doesn't resize → already fixed, uses native OS title bar
   - Old posts appear → `max_age_hours` is enforced in PostFilter

## File Map

| File | Purpose |
|------|---------|
| `run_scraper.py` | Entry point — GUI + background worker thread |
| `skills.py` | Scraping logic: feed, explore, search, virality scoring |
| `interceptor.py` | Passive network interception, PostData, PostFilter |
| `browser_core.py` | Stealth Playwright browser with media blocking |
| `auth.py` | Instagram login flow (headed browser) |
| `web_launcher.py` | pywebview window creation |
| `mcp_server.py` | MCP server for Claude Code (6 tools incl. launch_gui) |
| `ui_templates/launcher.html` | Full UI: settings panel + results dashboard |
| `install_all.py` | Universal cross-platform installer |

## Rules

- NEVER commit `storage_state.json` (user's Instagram session)
- Browser runs `headless=False` (Instagram blocks headless)
- PostFilter always uses `max_age_hours` to filter old posts
- Search scrolls limited to 12 per keyword
- All scraping happens in a daemon thread, GUI stays responsive
