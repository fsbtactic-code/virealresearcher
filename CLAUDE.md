# Banana Parser — Claude Code Instructions

## Slash Commands

- `/banana-install` — Установить всё: зависимости, Playwright, sentence-transformers, проверить готовность
- `/banana-auth` — Открыть защищенное окно для входа в Instagram
- `/banana-run` — Запустить главное окно парсера (в отдельном процессе)
- `/banana-debug` — Полная автодиагностика + автоисправление
- `/banana-keywords` — Составить точный список ключей для ниши (исключая двусмысленные)

## What is this?

Banana Parser — Instagram stealth scraper. Десктопное приложение (pywebview + Playwright) для поиска вирусного контента конкурентов. Поддерживает двухуровневую фильтрацию: точные ключевые слова + AI семантический классификатор.

## Quick Setup

```bash
python install_all.py    # установка всего (включая sentence-transformers)
python auth.py           # авторизация Instagram (один раз)
python run_scraper.py    # запуск GUI
```

## If something breaks

1. Read `.ai-context.md` for architecture and known issues
2. Common fixes:
   - `storage_state.json not found` → run `python auth.py`
   - `playwright` errors → run `python -m playwright install chromium`
   - Import errors → run `pip install -r requirements.txt`
   - AI classifier not loading → run `pip install sentence-transformers` (уже должен быть)
   - Model download slow → первый запуск скачивает `paraphrase-multilingual-MiniLM-L12-v2` (~118MB)
   - Window doesn't resize → already fixed, uses native OS title bar
   - Old posts appear → `max_age_hours` is enforced in PostFilter

## File Map

| File | Purpose |
|------|---------|
| `run_scraper.py` | Entry point — GUI + background worker thread + AI status methods |
| `skills.py` | Scraping logic: feed, explore, search, virality scoring, AI warm-up |
| `interceptor.py` | Passive network interception, PostData, PostFilter + AI fallback |
| `ai_classifier.py` | **[NEW]** Semantic topic classifier (sentence-transformers, graceful fallback) |
| `browser_core.py` | Stealth Playwright browser with media blocking |
| `auth.py` | Instagram login flow (headed browser) |
| `web_launcher.py` | pywebview window creation |
| `mcp_server.py` | MCP server for Claude Code (6 tools incl. launch_gui) |
| `ui_templates/launcher.html` | Full UI: settings panel + results dashboard |
| `install_all.py` | Universal cross-platform installer |

## Filtering Architecture (2-level)

```
Collected post
  ├─ Level 1: Exact keyword match (text / alt-text / subtitles)
  │   ├─ PASS → include post
  │   └─ FAIL →
  │       └─ Level 2: AI semantic classification (if enabled)
  │           ├─ similarity >= 0.35 → include post
  │           ├─ similarity < 0.35  → discard post
  │           └─ model not ready    → bypass (include)
  └─ (no keywords set) → include all posts
```

## Rules

- NEVER commit `storage_state.json` (user's Instagram session)
- Browser runs `headless=False` (Instagram blocks headless)
- PostFilter always uses `max_age_hours` to filter old posts
- Search scrolls limited to 12 per keyword
- All scraping happens in a daemon thread, GUI stays responsive
- AI model loads in a background thread (never blocks UI)
- ai_classifier.py MUST have graceful fallback — never crash if sentence-transformers missing
