"""
web_launcher.py — Native window launcher for Banana Parser GUI.
Uses pywebview (Edge WebView2 on Windows, WKWebView on macOS) to show
launcher.html as a desktop app.
"""
import logging
import os
import sys
from pathlib import Path

import webview

PROJECT_ROOT  = Path(__file__).parent.resolve()
LAUNCHER_HTML = PROJECT_ROOT / "ui_templates" / "launcher.html"

log = logging.getLogger("Banana Parser")

global_window = None


def get_window():
    return global_window


def launch_gui(api_instance) -> None:
    """
    Creates and shows a native window with launcher.html.
    Binds the given API instance to the JS bridge.
    This call BLOCKS until the window is closed.
    """
    global global_window

    log.info("-" * 60)
    log.info("[ GUI ]  launch_gui() — открываем нативное окно")
    log.info(f"   HTML: {LAUNCHER_HTML}")
    log.info(f"   Существует: {LAUNCHER_HTML.exists()}")

    if not LAUNCHER_HTML.exists():
        log.critical(f"[ ERROR ] launcher.html не найден по пути: {LAUNCHER_HTML}")
        return

    log.info(f"   API instance: {type(api_instance).__name__}")

    try:
        global_window = webview.create_window(
            title='Banana Parser',
            url=str(LAUNCHER_HTML.resolve()),
            js_api=api_instance,
            width=580,
            height=660,
            min_size=(400, 520),
            resizable=True,
            frameless=False,  # Native OS title bar — required for macOS resize/drag
            background_color='#08080a',
        )
        log.info("   [ OK ] webview.create_window() — создано")
        log.info(f"   Окно: {global_window}")
    except Exception as e:
        log.critical(f"[ ERROR ] Ошибка webview.create_window(): {e}")
        return

    log.info("[ RUN ] webview.start() — запуск event loop (блокирующий вызов)...")
    try:
        if sys.platform == "win32":
            webview.start(gui='edgechromium', debug=False)
        elif sys.platform == "darwin":
            # macOS: use default WKWebView (no extra args needed)
            webview.start(debug=False)
        else:
            # Linux: GTK WebView
            webview.start(debug=False)
        log.info("[ OK ] webview.start() завершён (окно закрыто)")
    except Exception as e:
        log.error(f"[ ERROR ] Ошибка webview.start(): {e}")
