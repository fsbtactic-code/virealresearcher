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


CUSTOM_CSS = """
/* Banana Parser Liquid Glass Theme Override for Instagram Login */
body, html, main, article {
    background-color: #08080a !important;
    color: #ffffff !important;
}

/* Force dark backgrounds on container elements */
div {
    background-color: transparent !important;
}
.x1qjc9v5, .x9f619 {
    background-color: transparent !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
    color: #fff !important;
}

/* Main login box targeting */
form, div[class*="x1cy8zhl"], div[class*="x1xy1w5w"] {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 0 40px rgba(255, 46, 147, 0.2) !important;
}

/* Inputs */
input {
    background-color: rgba(0, 0, 0, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: #fff !important;
    border-radius: 12px !important;
}
input:focus {
    border-color: #ff2e93 !important;
}

/* Login Button */
button[type="submit"], div[role="button"][tabindex="0"] {
    background: linear-gradient(135deg, #ff2e93, #ff8a00) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-weight: 600 !important;
    opacity: 1 !important;
    transition: all 0.2s ease !important;
}
button[type="submit"]:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 15px rgba(255, 46, 147, 0.4) !important;
}

/* Text */
span, p, h1, h2 {
    color: #e0e0e0 !important;
}
a {
    color: #ff8a00 !important;
}

/* Instagram sprite logo inversion */
i[data-visualcompletion="css-img"] {
    filter: invert(1) hue-rotate(180deg) brightness(2) !important;
}
"""


def print_banner():
    print()
    print(_c("95", "  ╔══════════════════════════════════════════════════════════════╗"))
    print(_c("95", "  ║") + BOLD("  🍌 Banana Master — Instagram Stealth Scraper              ") + _c("95", "║"))
    print(_c("95", "  ║") + "                                                              " + _c("95", "║"))
    print(_c("95", "  ║") + "  " + CYAN("Авторизация Instagram") + "                                       " + _c("95", "║"))
    print(_c("95", "  ╚══════════════════════════════════════════════════════════════╝"))
    print()


def print_warning():
    print(_c("41;97", "  ⚠️  ВНИМАНИЕ — ПРОЧИТАЙТЕ ПЕРЕД ВХОДОМ  ⚠️                     "))
    print()
    print(YELLOW("  ┌──────────────────────────────────────────────────────────┐"))
    print(YELLOW("  │") + RED("  🚫 НЕ используйте свой ОСНОВНОЙ аккаунт Instagram!     ") + YELLOW("│"))
    print(YELLOW("  │                                                          │"))
    print(YELLOW("  │") + "  Instagram может временно ограничить аккаунт, который    " + YELLOW("│"))
    print(YELLOW("  │") + "  используется для автоматического сбора данных.           " + YELLOW("│"))
    print(YELLOW("  │                                                          │"))
    print(YELLOW("  │") + GREEN("  ✅ Создайте ОТДЕЛЬНЫЙ аккаунт для парсинга              ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  ✅ Подождите 2-3 дня после создания перед парсингом     ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  ✅ Подпишитесь на 10-20 аккаунтов для правдоподобности  ") + YELLOW("│"))
    print(YELLOW("  │") + GREEN("  ✅ Не запускайте парсинг чаще 2 раз в сутки             ") + YELLOW("│"))
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
        print(RED("  ❌ Playwright не установлен!"))
        print("  Запустите: pip install playwright && playwright install chromium")
        return False

    print(CYAN("  🚀 Запускаю браузер..."))
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

        # Navigate to Instagram login (Fast commit + Selector polling)
        print(CYAN("  🌐 Подключаюсь к Instagram..."))
        try:
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="commit", timeout=30000)
            # Wait for any form element or cookie banner
            await page.wait_for_selector('input[name="username"], button:has-text("Allow"), button:has-text("Разрешить")', timeout=60000)
            print(GREEN("  ✅ Страница логина загружена."))
        except Exception as e:
            print(YELLOW(f"  ⚠️  Медленная загрузка (но продолжаем): {e}"))

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

        # --- INJECT CUSTOM CSS THEME ---
        try:
            print(CYAN("  💅 Применяю фирменный дизайн Banana Parser..."))
            await page.add_style_tag(content=CUSTOM_CSS)
        except Exception as e:
            pass


        print(_c("43;30", "  ⏳ Войдите в Instagram в открытом браузере...                  "))
        print()
        print(DIM("  Сессия сохранится автоматически когда вы войдёте."))
        print(DIM("  (Или нажмите Enter для ручного сохранения)"))
        print()

        # Auto-detect login: poll URL until it leaves /login/
        logged_in = False
        max_wait = 300  # 5 minutes max
        for _ in range(max_wait * 2):  # check every 0.5s
            try:
                current_url = page.url
                # Logged in = no longer on login/challenge page
                if ("instagram.com" in current_url
                    and "/login" not in current_url
                    and "/challenge" not in current_url
                    and "/accounts/" not in current_url):
                    logged_in = True
                    print()
                    print(GREEN("  🎉 Вход обнаружен! Сохраняю сессию..."))
                    # Wait a bit for cookies to settle
                    await asyncio.sleep(3)
                    break
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
                print(YELLOW(f"  ⚠️  URL: {current_url}"))
                retry = input(BOLD("  Всё равно сохранить сессию? (да/нет): ")).strip().lower()
                if retry not in ("да", "yes", "y", "д"):
                    await browser.close()
                    print(RED("  ❌ Отменено."))
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
    print(_c("42;97", "  ✅ Сессия сохранена!                                           "))
    print()
    print(f"  📁 Файл:    {GREEN(str(STORAGE_STATE))}")
    print(f"  🍪 Cookies: {BOLD(str(cookies_count))}")
    print(f"  🌐 Origins: {BOLD(str(origins_count))}")
    print()
    print(CYAN("  🎯 Теперь можно запускать парсинг:"))
    print(f"     {DIM('python run_scraper.py')}")
    print()
    print(_c("95", "  ──────────────────────────────────────────────────────────────"))
    print(f"  🍌 Создано {BOLD('Banana Master')} | t.me/banana_marketing")
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
        print(RED("  ❌ Прервано пользователем."))
        sys.exit(1)
