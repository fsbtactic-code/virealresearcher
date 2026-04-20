"""
test_session.py — Быстрая проверка сохранённой Instagram-сессии.
Открывает браузер с cookies из storage_state.json и показывает ленту.
"""
import asyncio
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT  = Path(__file__).parent.resolve()
STORAGE_STATE = PROJECT_ROOT / "storage_state.json"

def _c(code, t): return f"\033[{code}m{t}\033[0m"
GREEN  = lambda t: _c("92", t)
RED    = lambda t: _c("91", t)
YELLOW = lambda t: _c("93", t)
CYAN   = lambda t: _c("96", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)


def check_storage() -> dict | None:
    """Читает и валидирует storage_state.json."""
    if not STORAGE_STATE.exists():
        print(RED("  [ ERROR ] storage_state.json не найден — сначала запустите auth.py"))
        return None

    with open(STORAGE_STATE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cookies = data.get("cookies", [])
    ig_cookies = [c for c in cookies if "instagram.com" in c.get("domain", "")]

    print(f"  📁 Файл:          {DIM(str(STORAGE_STATE))}")
    print(f"  🍪 Всего cookies: {BOLD(str(len(cookies)))}")
    print(f"  📸 IG cookies:    {BOLD(str(len(ig_cookies)))}")

    # Ищем sessionid — главный маркер авторизации
    session_cookie = next((c for c in ig_cookies if c.get("name") == "sessionid"), None)
    if session_cookie:
        val = session_cookie.get("value", "")
        print(f"  [ AUTH ] sessionid:     {GREEN(val[:12] + '...' + val[-6:])}")
        return data
    else:
        print(YELLOW("  [ WARN ]  sessionid не найден — сессия может быть невалидна"))
        return data


async def verify_session():
    """Открывает headed браузер с сохранёнными cookies, проверяет сессию."""
    print()
    print(_c("95", "  ╔══════════════════════════════════════════════════════════════╗"))
    print(_c("95", "  ║") + BOLD("🟦  Banana Parser — Проверка сессии Instagram               ") + _c("95", "║"))
    print(_c("95", "  ╚══════════════════════════════════════════════════════════════╝"))
    print()

    data = check_storage()
    if data is None:
        return False

    print()
    print(CYAN("  [ RUN ] Открываю браузер с сохранёнными cookies..."))
    print(DIM("  (Окно закроется автоматически через 10 секунд)"))
    print()

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=430,900",
                "--no-first-run",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 430, "height": 900},
            storage_state=str(STORAGE_STATE),
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ru-RU",
        )

        page = await context.new_page()

        print(CYAN("  🌐 Перехожу на instagram.com..."))
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(YELLOW(f"  [ WARN ]  Медленная загрузка: {e}"))

        await asyncio.sleep(3)
        current_url = page.url
        print(f"  📍 URL: {DIM(current_url)}")

        # Определяем статус по URL и DOM
        logged_in = False
        username = None

        if "/accounts/login" in current_url or "/accounts/emailsignup" in current_url:
            print(RED("  [ ERROR ] СЕССИЯ УСТАРЕЛА — Instagram перенаправил на логин"))
            print(YELLOW("     Запустите python auth.py снова для обновления сессии"))
        else:
            # Пробуем вытащить username из профиля
            try:
                # Instagram хранит username в мета-теге og:title или в span
                title = await page.title()
                # Также проверим ссылку на профиль
                profile_link = await page.query_selector('a[href*="/"][role="link"][tabindex="0"]')
                if profile_link:
                    href = await profile_link.get_attribute("href")
                    if href and href != "/" and len(href) > 1:
                        username = href.strip("/")

                logged_in = True
                print(GREEN("  [ OK ] СЕССИЯ АКТИВНА — Instagram открылся без логина!"))
                if username:
                    print(GREEN(f"  👤 Аккаунт:  @{username}"))
                print(f"  📰 Заголовок: {DIM(title[:60])}")
            except Exception:
                logged_in = True
                print(GREEN("  [ OK ] СЕССИЯ АКТИВНА"))

        print()
        print(DIM("  Окно закроется через 8 секунд..."))
        await asyncio.sleep(8)
        await browser.close()

    print()
    if logged_in:
        print(_c("42;97", "  [ OK ] Сессия валидна. Можно запускать парсинг:              "))
        print()
        print(f"     {BOLD('python run_scraper.py')}")
    else:
        print(_c("41;97", "  [ ERROR ] Сессия недействительна. Запустите: python auth.py     "))
    print()

    return logged_in


if __name__ == "__main__":
    import os
    os.chdir(PROJECT_ROOT)
    try:
        result = asyncio.run(verify_session())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print()
        print(RED("  [ ERROR ] Прервано."))
        sys.exit(1)
