#!/usr/bin/env python3
"""
install_all.py — Universal installer for Banana Parser.

Works on Windows, macOS, and Linux.
Installs all Python dependencies + Playwright browsers.
Run: python install_all.py
"""
import os
import subprocess
import sys
import platform
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Colors
if sys.platform == "win32":
    os.system("")  # Enable ANSI on Windows

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PROJECT_ROOT = Path(__file__).parent.resolve()

def log_ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def log_warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def log_err(msg):
    print(f"  {RED}✗{RESET} {msg}")

def log_step(msg):
    print(f"\n{CYAN}{BOLD}▸ {msg}{RESET}")

def run(cmd, **kwargs):
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300, **kwargs
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        return False, str(e)


def check_python():
    """Verify Python version >= 3.10."""
    log_step("Checking Python")
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        log_ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        log_err(f"Python {v.major}.{v.minor} — need Python 3.10+")
        if sys.platform == "win32":
            print(f"\n  {YELLOW}Install Python: https://python.org/downloads{RESET}")
        elif sys.platform == "darwin":
            print(f"\n  {YELLOW}Run: brew install python@3.12{RESET}")
        else:
            print(f"\n  {YELLOW}Run: sudo apt install python3.12{RESET}")
        return False


def check_macos_tools():
    """macOS: verify Xcode Command Line Tools (needed for pyobjc)."""
    if sys.platform != "darwin":
        return True
    log_step("macOS: проверка Xcode CLT")
    ok, _ = run(["xcode-select", "-p"])
    if ok:
        log_ok("Xcode Command Line Tools установлены")
        return True
    else:
        log_warn("Xcode CLT не найдены — запускаю установку...")
        print(f"  {YELLOW}→ Появится системный диалог. Нажмите 'Install' и дождитесь завершения.{RESET}")
        os.system("xcode-select --install")
        log_warn("После завершения установки CLT снова запустите: python3 install_all.py")
        return False


def install_pip_deps():
    """Install requirements.txt."""
    log_step("Установка зависимостей (pip)")
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        log_err("requirements.txt не найден!")
        return False

    ok, out = run([sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"])
    if ok:
        log_ok("Все пакеты установлены")
        return True
    else:
        log_err(f"pip install failed:\n{out[-500:]}")
        log_warn("Обновляю pip и пробую снова...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
        ok2, out2 = run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        if ok2:
            log_ok("Пакеты установлены (после обновления pip)")
            return True
        log_err(f"Повторная попытка тоже не удалась:\n{out2[-500:]}")
        return False


def install_playwright():
    """Install Playwright Chromium browser."""
    log_step("Установка Playwright Chromium")

    ok, out = run([sys.executable, "-m", "playwright", "install", "chromium"])
    if ok:
        log_ok("Chromium установлен")
    else:
        log_err(f"Ошибка установки Chromium:\n{out[-500:]}")
        return False

    # Install system deps on Linux only (NOT needed on macOS/Windows)
    if sys.platform == "linux":
        log_warn("Устанавливаю системные зависимости (может потребовать sudo)...")
        ok2, out2 = run(["sudo", sys.executable, "-m", "playwright", "install-deps", "chromium"])
        if not ok2:
            log_warn(f"install-deps: {out2[-300:]}")
            log_warn("Возможно, потребуется запустить вручную: sudo playwright install-deps")

    return True


def verify_imports():
    """Verify all critical imports work."""
    log_step("Проверка импортов")
    modules = [
        ("playwright.async_api", "Playwright"),
        ("playwright_stealth", "Playwright Stealth"),
        ("webview", "PyWebView"),
        ("pydantic", "Pydantic"),
        ("mcp", "MCP"),
    ]
    all_ok = True
    for mod, name in modules:
        try:
            __import__(mod)
            log_ok(name)
        except ImportError as e:
            log_err(f"{name} — {e}")
            all_ok = False

    # Optional: sentence-transformers for AI semantic classification
    try:
        import sentence_transformers  # noqa: F401
        log_ok(f"sentence-transformers {sentence_transformers.__version__} (AI классификатор)")
    except ImportError:
        log_warn("sentence-transformers не найден — ИИ-фильтрация будет недоступна")
        log_warn("Установить: pip install sentence-transformers")

    # macOS-specific: check pyobjc
    if sys.platform == "darwin":
        try:
            import objc  # noqa: F401
            log_ok("pyobjc (macOS WebView support)")
        except ImportError:
            log_warn("pyobjc не найден — WebView может не работать на macOS")
            log_warn("Запустите: pip install pyobjc-framework-WebKit pyobjc-core")

    return all_ok


def create_output_dir():
    """Ensure output directory exists."""
    out = PROJECT_ROOT / "output"
    out.mkdir(exist_ok=True)
    log_ok("output/ directory ready")


def save_project_path():
    """Save absolute path to home directory for global CLI access."""
    try:
        home_path_file = Path.home() / ".banana_parser_path"
        home_path_file.write_text(str(PROJECT_ROOT), encoding="utf-8")
        log_ok(f"Путь к проекту зафиксирован: {home_path_file}")
    except Exception as e:
        log_warn(f"Не удалось сохранить глобальный путь проекта: {e}")


def main():
    print()
    print(f"{BOLD}{'='*56}{RESET}")
    print(f"{BOLD}  Banana Parser — Installation{RESET}")
    print(f"{DIM}  {platform.system()} {platform.release()} | Python {sys.version.split()[0]}{RESET}")
    print(f"{BOLD}{'='*56}{RESET}")

    steps = [
        ("Python ≥ 3.10", check_python),
        ("pip зависимости", install_pip_deps),
        ("Playwright Chromium", install_playwright),
        ("Импорты", verify_imports),
    ]

    # Insert macOS tools check on darwin
    if sys.platform == "darwin":
        steps.insert(1, ("macOS Xcode CLT", check_macos_tools))

    for name, func in steps:
        if not func():
            print(f"\n{RED}{BOLD}  ✗ Установка прервана на шаге: {name}{RESET}")
            print(f"  Исправьте ошибку выше и запустите снова: python install_all.py\n")
            sys.exit(1)

    create_output_dir()
    save_project_path()

    print(f"\n{'='*56}")
    print(f"  {GREEN}{BOLD}✓ Banana Parser успешно установлен!{RESET}")
    print()
    print(f"  {BOLD}Запуск:{RESET}")
    print(f"  {CYAN}1.{RESET} python auth.py          {DIM}← авторизация Instagram (один раз){RESET}")
    print(f"  {CYAN}2.{RESET} python run_scraper.py    {DIM}← запуск парсера{RESET}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()
