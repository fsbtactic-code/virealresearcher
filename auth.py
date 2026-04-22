"""
auth.py — Instagram login flow with Playwright.

Opens a headed Chromium browser for manual Instagram login.
Saves session cookies to storage_state.json for headless reuse.
Includes a safety warning about using a secondary account.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.resolve()
STORAGE_STATE = PROJECT_ROOT / "storage_state.json"

# ── Terminal color helpers ──
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

RED    = lambda t: _c("91", t)
YELLOW = lambda t: _c("93", t)
GREEN  = lambda t: _c("92", t)
CYAN   = lambda t: _c("96", t)
BOLD   = lambda t: _c("1", t)
DIM    = lambda t: _c("2", t)


CUSTOM_CSS = ""  # CSS injection disabled



def print_banner():
    print()
    print(_c("95", "  ╔══════════════════════════════════════════════════════════════╗"))
    print(_c("95", "  ║") + BOLD("🟦  Banana Parser — Instagram Stealth Scraper              ") + _c("95", "║"))
    print(_c("95", "  ║") + "                                                              " + _c("95", "║"))
    print(_c("95", "  ║") + "  " + CYAN("Авторизация Instagram") + "                                       " + _c("95", "║"))
    print(_c("95", "  ╚══════════════════════════════════════════════════════════════╝"))
    print()


def print_warning():
    print(_c("41;97", "  [ WARN ]  ВНИМАНИЕ — ПРОЧИТАЙТЕ ПЕРЕД ВХОДОМ  [ WARN ]                     "))
    print()
    print(YELLOW("  ┌──────────────────────────────────────────────────────────┐"))
    print(YELLOW("  │") + RED("  🚫 НЕ используйте свой ОСНОВНОЙ аккаунт Instagram!     ") + YELLOW("│"))
    print(YELLOW("  │                                                          │"))
    print(YELLOW("  │") + "  Instagram может временно ограничить аккаунт, который    " + YELLOW("│"))
    print(YELLOW("  │") + "  используется для автоматического сбора данных.           " + YELLOW("│"))
    print(YELLOW("  │                                                          │"))
    print(YELLOW("  │") + GREEN("  [ OK ] Создайте ОТДЕЛЬНЫЙ аккаунт для парсинга              ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  [ OK ] Подождите 2-3 дня после создания перед парсингом     ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  [ OK ] Подпишитесь на 10-20 аккаунтов для правдоподобности  ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  [ OK ] Не запускайте парсинг чаще 2 раз в сутки             ") + YELLOW("│"))
    print(YELLOW("  │                                                          │"))
    print(YELLOW("  │") + DIM("  Мы заботимся о вашей безопасности 🔒                    ") + YELLOW("│"))
    print(YELLOW("  └──────────────────────────────────────────────────────────┘"))
    print()


def print_instructions():
    print(CYAN("  📋 Инструкция:"))
    print()
    print("  1️⃣  Откроется браузер с Instagram")
    print("  2️⃣  Войдите в " + BOLD("ЗАПАСНОЙ") + " аккаунт вручную")
    print("  3️⃣  Если появится двухфакторная аутентификация — пройдите её")
    print("  4️⃣  Дождитесь загрузки ленты (домашняя страница)")
    print("  5️⃣  " + GREEN("Нажмите Enter в этом окне") + " чтобы сохранить сессию")
    print()


async def run_auth():
    """Launch a headed browser for manual Instagram login."""
    print_banner()
    print_warning()

    # Ask for confirmation
    print(f"  Текущая папка: {DIM(str(PROJECT_ROOT))}")
    if STORAGE_STATE.exists():
        print(f"  ⚡ Найдена существующая сессия: {DIM(str(STORAGE_STATE))}")
        print(YELLOW("     Она будет перезаписана при новом входе."))
    print()

    # Пропускаем ручное подтверждение (Claude сам предупредит в чате)
    print(GREEN("  ⚡ Окно авторизации открывается, пожалуйста подождите..."))

    print()
    print_instructions()

    # Import Playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(RED("  [ ERROR ] Playwright не установлен!"))
        print("  Запустите: pip install playwright && playwright install chromium")
        return False

    print(CYAN("  [ RUN ] Запускаю браузер..."))
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=420,780",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 420, "height": 780},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = await context.new_page()

        # Navigate to instagram.com root (avoids 429 on /accounts/login/ direct)
        print(CYAN("  🌐 Подключаюсь к Instagram..."))
        try:
            await page.goto("https://www.instagram.com/", wait_until="commit", timeout=30000)
            # Wait for login form OR already logged-in feed
            await page.wait_for_selector(
                'input[name="username"], a[href="/"][role="link"], button:has-text("Log in"), button:has-text("Войти")',
                timeout=60000
            )
            print(GREEN("  [ OK ] Instagram загружен."))
        except Exception as e:
            print(YELLOW(f"  [ WARN ]  Медленная загрузка (но продолжаем): {e}"))
        # Dismiss cookie banner if present
        try:
            cookie_btn = await page.wait_for_selector(
                'button:has-text("Allow"), button:has-text("Разрешить"), '
                'button:has-text("Accept"), button:has-text("Принять")',
                timeout=5000,
            )
            if cookie_btn:
                await cookie_btn.click()
        except Exception:
            pass

        # CSS injection disabled — Instagram native UI used

        print(_c("43;30", "  [ WAIT ] Войдите в Instagram в открытом браузере...                  "))
        print()
        print(DIM("  Сессия сохранится автоматически когда вы войдёте."))
        print(DIM("  (Или нажмите Enter для ручного сохранения)"))
        print()

        # Auto-detect login: poll context cookies until sessionid appears
        # URL check alone is unreliable — IG shows instagram.com/ even when NOT logged in
        logged_in = False
        max_wait = 300  # 5 minutes max
        for tick in range(max_wait * 2):  # check every 0.5s
            try:
                cookies = await context.cookies()
                session_cookie = next(
                    (c for c in cookies if c.get("name") == "sessionid" and "instagram" in c.get("domain", "")),
                    None
                )
                if session_cookie:
                    logged_in = True
                    print()
                    print(GREEN("  🎉 sessionid получен! Сохраняю сессию..."))
                    # Extra wait for all cookies to settle after login
                    await asyncio.sleep(4)
                    break

                # Print progress every 10 seconds
                if tick % 20 == 0 and tick > 0:
                    elapsed = tick // 2
                    print(DIM(f"  ⏱ Ожидание входа... {elapsed}с"), end="\r")

            except Exception:
                pass

            # Check if user pressed Enter (non-blocking on Windows is tricky,
            # so we just poll URL)
            await asyncio.sleep(0.5)

        if not logged_in:
            print()
            print(YELLOW("  ⏱ Тайм-аут 5 минут. Проверяю текущий статус..."))
            current_url = page.url
            if "login" in current_url or "challenge" in current_url:
                print(YELLOW(f"  [ WARN ]  URL: {current_url}"))
                retry = input(BOLD("  Всё равно сохранить сессию? (да/нет): ")).strip().lower()
                if retry not in ("да", "yes", "y", "д"):
                    await browser.close()
                    print(RED("  [ ERROR ] Отменено."))
                    return False

        # Save session state
        storage = await context.storage_state()
        with open(STORAGE_STATE, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)

        await browser.close()

    # Verify saved data
    cookies_count = len(storage.get("cookies", []))
    origins_count = len(storage.get("origins", []))

    print()
    print(_c("42;97", "  [ OK ] Сессия сохранена!                                           "))
    print()
    print(f"  📁 Файл:    {GREEN(str(STORAGE_STATE))}")
    print(f"  🍪 Cookies: {BOLD(str(cookies_count))}")
    print(f"  🌐 Origins: {BOLD(str(origins_count))}")
    print()
    print(CYAN("  [ TARGET ] Теперь можно запускать парсинг:"))
    print(f"     {DIM('python run_scraper.py')}")
    print()
    print(_c("95", "  ──────────────────────────────────────────────────────────────"))
    print("  🟦 Banana Parser — t.me/banana_marketing")
    print(_c("95", "  ──────────────────────────────────────────────────────────────"))
    print()

    return True


if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    try:
        result = asyncio.run(run_auth())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print()
        print(RED("  [ ERROR ] Прервано пользователем."))
        sys.exit(1)
