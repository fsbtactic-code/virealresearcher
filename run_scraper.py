"""
run_scraper.py — Standalone scraper launcher with GUI settings.

Shows a native window for configuring scrape parameters, then runs
the master_viral_hunter pipeline and displays an inline dashboard.
"""
import asyncio
import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
import io

# ── Force UTF-8 on Windows console ──
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

# ══════════════════════════════════════════════
#  LOGGING SETUP
# ══════════════════════════════════════════════
LOG_FILE = PROJECT_ROOT / "Banana Parser.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("Banana Parser")

log.info("=" * 60)
log.info("🟦 Banana Parser — ЗАПУСК")
log.info(f"   Время:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log.info(f"   Python:       {sys.version}")
log.info(f"   Platform:     {sys.platform}")
log.info("=" * 60)

# ── Imports after logging init ──
try:
    log.info("[ OK ] interceptor.py импортирован")
except ImportError as e:
    log.error(f"[ ERROR ] Не удалось импортировать interceptor: {e}")

try:
    from web_launcher import launch_gui, get_window
    log.info("[ OK ] web_launcher.py импортирован")
except ImportError as e:
    log.critical(f"[ ERROR ] Не удалось импортировать web_launcher: {e}")
    sys.exit(1)

# ── AI Classifier (optional dependency) ──
try:
    from ai_classifier import classifier as _ai_classifier, warm_up_in_background as _ai_warmup
    log.info("[ OK ] ai_classifier.py импортирован")
except ImportError:
    _ai_classifier = None
    _ai_warmup = None
    log.warning("[ WARN ] ai_classifier.py не найден — AI-режим недоступен")

# ── Terminal helpers ──
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

BOLD   = lambda t: _c("1", t)
DIM    = lambda t: _c("2", t)
PURPLE = lambda t: _c("95", t)


def print_banner():
    print()
    print(PURPLE("  ╔══════════════════════════════════════════════════════════════╗"))
    print(PURPLE("  ║") + BOLD("🟦  Banana Parser — Instagram Stealth Scraper                        ") + PURPLE("║"))
    print(PURPLE("  ║") + DIM("  v3.0 | Stealth Mode | Turbo AI Search                        ") + PURPLE("║"))
    print(PURPLE("  ╚══════════════════════════════════════════════════════════════╝"))
    print()


def check_session() -> bool:
    """Checks if storage_state.json exists and has enough IG cookies."""
    state_file = PROJECT_ROOT / "storage_state.json"
    if not state_file.exists():
        log.warning("[ ERROR ] storage_state.json не найден — авторизация не выполнена")
        return False
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.error(f"[ ERROR ] Ошибка чтения storage_state.json: {e}")
        return False
    cookies = data.get("cookies", [])
    ig_cookies = [c for c in cookies if "instagram" in c.get("domain", "")]
    if len(ig_cookies) < 3:
        return False
    log.info(f"[ OK ] Сессия АКТИВНА ({len(ig_cookies)} IG-cookies)")
    return True


# ══════════════════════════════════════════════
#  GUI API  (вызывается из JavaScript)
# ══════════════════════════════════════════════
class WebWorkerApi:

    def __init__(self):
        self._stop_event = threading.Event()

    def stopScraping(self):
        """JS → Python: request graceful stop."""
        log.info("[ NET ] stopScraping() — запрос остановки")
        self._stop_event.set()

    def getAuthStatus(self):
        return check_session()

    def getAiStatus(self):
        """JS → Python: returns AI classifier status string for UI indicator."""
        if _ai_classifier is None:
            return "unavailable"
        return _ai_classifier.get_status()

    def getAiStatusText(self):
        """JS → Python: returns Russian UI status string."""
        if _ai_classifier is None:
            return "AI недоступен"
        return _ai_classifier.get_status_text()

    def startAuth(self):
        import subprocess
        log.info("[ NET ] startAuth() — запуск auth.py")
        try:
            subprocess.run(
                [sys.executable, "auth.py"],
                check=True, capture_output=True, text=True
            )
            return True
        except Exception as e:
            log.error(f"[ ERROR ] Ошибка авторизации: {e}")
            return False

    def toggleBrowser(self, show: bool):
        """Show or hide the headless browser window (e.g., to solve captchas)."""
        import browser_core

        gb = browser_core.global_browser
        loop = browser_core.global_loop

        if not gb or not getattr(gb, "_page", None):
            log.warning("[ WARN ] toggleBrowser: браузер ещё не запущен или уже закрыт.")
            return False

        if not loop or not loop.is_running():
            log.warning("[ WARN ] toggleBrowser: event loop не активен.")
            return False

        if show:
            log.info("👁️ Показываем окно браузера...")
            asyncio.run_coroutine_threadsafe(gb.show_window(), loop)
        else:
            log.info("🙈 Скрываем окно браузера...")
            asyncio.run_coroutine_threadsafe(gb.hide_window(), loop)
        return True

    def exportHTML(self, posts: list):
        """JS -> Python: Экспорт HTML через нативный SAVE диалог pywebview."""
        log.info("[ NET ] exportHTML() — экспорт красивого HTML")
        try:
            import webview
            w = get_window()
            if not w:
                return False
                
            dt = datetime.now().strftime("%Y%m%d_%H%M")
            fname = f"viral_report_{dt}.html"
            
            save_path = w.create_file_dialog(
                webview.SAVE_DIALOG, 
                directory='', 
                save_filename=fname
            )
            
            if save_path and isinstance(save_path, (list, tuple)):
                path = save_path[0]
            elif save_path:
                path = save_path
            else:
                return False # Отменил
                
            # Импортируем существующий генератор
            from ui_generator import generate_results_html
            generate_results_html(posts, path)
            log.info(f"[ OK ] HTML успешно сохранен: {path}")
            return True
        except Exception as e:
            log.error(f"[ ERROR ] Ошибка экспорта HTML: {e}")
            return False

    def startScraping(self, gui_data: dict):
        log.info("[ NET ] startScraping() — получены данные из GUI")
        log.info(f"   gui_data: {json.dumps(gui_data, indent=2, ensure_ascii=False)}")

        # ── Проверка сессии ──
        if not check_session():
            w = get_window()
            if w:
                w.evaluate_js("window.alert('Сначала выполните авторизацию!')")
            return

        # ── Сборка настроек ──
        settings = {
            "seed_keyword":           gui_data.get("keyword", "маркетинг"),
            "time_limit_hours":        gui_data.get("depth", 24),
            "top_n":                  gui_data.get("top_n", 30),
            "min_likes":              gui_data.get("min_likes", 0),
            "max_likes":              0,
            "min_comments":           0,
            "max_comments":           0,
            "max_followers":          0,
            "min_followers":          0,
            "exclude_zero_engagement": gui_data.get("no_zero", True),
            "scrape_explore":         gui_data.get("scrape_explore", True),
            "explore_limit":          gui_data.get("explore_limit", 80),
            "scrape_feed":            gui_data.get("scrape_feed", True),
            "feed_limit":             gui_data.get("feed_limit", 40),
            "feed_scrolls":           gui_data.get("feed_scrolls", 15),
            "explore_scrolls":        gui_data.get("explore_scrolls", 20),
            "fetch_images":           gui_data.get("fetch_images", True),
            "fetch_reels":            gui_data.get("fetch_reels", True),
            "fetch_carousels":        gui_data.get("fetch_carousels", True),
            "max_scrolls":            gui_data.get("max_scrolls", 60),
            "min_posts_target":       gui_data.get("min_posts", 10),
            "enable_deep_search":     gui_data.get("deep_search", False),
            "filter_keywords_raw":    gui_data.get("filter_keywords", ""),
            "only_ru_en":             gui_data.get("only_ru_en", False),
            # AI semantic classification
            "ai_topic_text":          gui_data.get("filter_keywords", ""),  # reuse topic field
            "ai_enabled":             gui_data.get("ai_recognition", False),
            "ai_threshold":           0.35,
        }

        log.info(f"📋 Настройки: keyword={settings['seed_keyword']}, depth={settings['time_limit_hours']}h")

        # ── Show loader ──
        w = get_window()
        if w:
            try:
                w.evaluate_js("showBeautifulLoader()")
            except Exception as e:
                log.error(f"[ ERROR ] showBeautifulLoader: {e}")

        # ── Сброс stop_event ──
        self._stop_event.clear()

        # ── Фоновый поток ──
        def _bg_worker():
            log.info("🧵 ФОНОВЫЙ ПОТОК ЗАПУЩЕН")
            try:
                from skills import master_viral_hunter

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                import browser_core
                browser_core.global_loop = loop

                def _progress_cb(stats: dict):
                    if w:
                        try:
                            # Forward stats dict to JavaScript
                            stats_json = json.dumps(stats, ensure_ascii=False)
                            w.evaluate_js(f"if(window.updateProgress) window.updateProgress({stats_json});")
                        except Exception as e:
                            log.debug(f"Progress update UI error: {e}")

                result = loop.run_until_complete(
                    master_viral_hunter(
                        seed_keyword=settings["seed_keyword"],
                        time_limit_hours=settings["time_limit_hours"],
                        top_n=settings["top_n"],
                        filters=settings,
                        include_deep_search=settings.get("enable_deep_search", False),
                        do_explore=settings.get("scrape_explore", True),
                        explore_limit=settings.get("explore_limit", 80),
                        explore_scrolls=settings.get("explore_scrolls", 20),
                        do_feed=settings.get("scrape_feed", True),
                        feed_limit=settings.get("feed_limit", 40),
                        feed_scrolls=settings.get("feed_scrolls", 15),
                        fetch_images=settings.get("fetch_images", True),
                        fetch_reels=settings.get("fetch_reels", True),
                        fetch_carousels=settings.get("fetch_carousels", True),
                        min_posts_target=settings.get("min_posts_target", 10),
                        max_scrolls=settings.get("max_scrolls", 60),
                        progress_cb=_progress_cb,
                        stop_event=self._stop_event,
                    )
                )
                loop.close()

                gathered   = result.get("total_collected", 0)
                top_posts  = result.get("top_posts", [])

                log.info(f"[ STAT ] Результат: {gathered} собрано, {len(top_posts)} в топе")

                # Save results
                results_path = Path(__file__).parent / "output" / "last_results.json"
                results_path.parent.mkdir(exist_ok=True)
                with open(results_path, "w", encoding="utf-8") as f:
                    json.dump(top_posts, f, ensure_ascii=False, indent=2)

                if w:
                    # Auto-resize window to near-fullscreen for dashboard
                    try:
                        w.evaluate_js("""
                            (function() {
                                var sw = screen.availWidth || 1280;
                                var sh = screen.availHeight || 720;
                                if (window.pywebview && window.pywebview.api) {
                                    // pywebview will handle
                                }
                            })();
                        """)
                        w.resize(
                            min(1400, 1920),   # width
                            min(900, 1080)     # height
                        )
                        w.move(40, 40)
                    except Exception:
                        pass

                    posts_json = json.dumps(top_posts, ensure_ascii=False)
                    posts_json_escaped = posts_json.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
                    js_call = f"finishLoading({gathered}, `{posts_json_escaped}`)"
                    try:
                        w.evaluate_js(js_call)
                        log.info("[ OK ] Дашборд загружен")
                    except Exception as e:
                        log.error(f"[ ERROR ] finishLoading: {e}")

            except Exception as e:
                import traceback
                log.error(f"💥 ОШИБКА: {traceback.format_exc()}")
                if w:
                    safe_msg = str(e).replace("'", "\\'").replace('"', '\\"')[:200]
                    try:
                        w.evaluate_js(f"window.alert('Упс! Ошибка парсинга: {safe_msg}'); window.location.reload();")
                    except Exception:
                        pass

            log.info("🧵 ФОНОВЫЙ ПОТОК ЗАВЕРШЁН")

        t = threading.Thread(target=_bg_worker, name="ScraperWorker", daemon=True)
        t.start()
        log.info(f"   [ OK ] Поток запущен: {t.name}")


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════
async def main():
    print_banner()
    log.info("🏁 main() запущен")

    session_ok = check_session()
    log.info(f"   Сессия: {'[ OK ] OK' if session_ok else '[ ERROR ] Нет сессии'}")

    api = WebWorkerApi()
    launch_gui(api)

    log.info("🏁 Приложение завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("⌨️  KeyboardInterrupt — выход")
