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
    log_step("Проверка Python")
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        log_ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        log_err(f"Python {v.major}.{v.minor} — нужен Python 3.10+")
        if sys.platform == "win32":
            print(f"\n  {YELLOW}Установите Python: https://python.org/downloads{RESET}")
        elif sys.platform == "darwin":
            print(f"\n  {YELLOW}brew install python@3.12{RESET}")
        else:
            print(f"\n  {YELLOW}sudo apt install python3.12{RESET}")
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
        # Try upgrading pip first
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

    # Install system deps on Linux
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
    ]
    all_ok = True
    for mod, name in modules:
        try:
            __import__(mod)
            log_ok(name)
        except ImportError as e:
            log_err(f"{name} — {e}")
            all_ok = False
    return all_ok


def create_output_dir():
    """Ensure output directory exists."""
    out = PROJECT_ROOT / "output"
    out.mkdir(exist_ok=True)
    log_ok("output/ directory ready")


def main():
    print()
    print(f"{BOLD}{'='*56}{RESET}")
    print(f"{BOLD}  🍌 Banana Parser — Установка{RESET}")
    print(f"{DIM}  {platform.system()} {platform.release()} | Python {sys.version.split()[0]}{RESET}")
    print(f"{BOLD}{'='*56}{RESET}")

    steps = [
        ("Python ≥ 3.10", check_python),
        ("pip зависимости", install_pip_deps),
        ("Playwright Chromium", install_playwright),
        ("Импорты", verify_imports),
    ]

    for name, func in steps:
        if not func():
            print(f"\n{RED}{BOLD}  ✗ Установка прервана на шаге: {name}{RESET}")
            print(f"  Исправьте ошибку выше и запустите снова: python install_all.py\n")
            sys.exit(1)

    create_output_dir()

    # Save absolute path to home directory for global access
    try:
        home_path_file = Path.home() / ".banana_parser_path"
        home_path_file.write_text(str(PROJECT_ROOT), encoding="utf-8")
        log_ok(f"Путь к проекту зафиксирован: {home_path_file}")
    except Exception as e:
        log_warn(f"Не удалось сохранить глобальный путь проекта: {e}")

    print(f"\n{'='*56}")
    print(f"  {GREEN}{BOLD}✓ Всё установлено!{RESET}")
    print()
    print(f"  {BOLD}Запуск:{RESET}")
    print(f"  {CYAN}1.{RESET} python auth.py          {DIM}← авторизация (один раз){RESET}")
    print(f"  {CYAN}2.{RESET} python run_scraper.py    {DIM}← запуск парсера{RESET}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()
