# Железобетонная Установка: macOS (Apple Silicon / Intel)

Скопируйте скрипт настройки ниже и вставьте в Terminal.app или iTerm2.

## Автоматическая настройка (Bash / ZSH)

```bash
# 1. Установка базовых инструментов Xcode (если не установлены)
xcode-select --install || true

# 2. Скачивание репозитория 
git clone https://github.com/fsbtactic-code/virealresearcher.git
cd virealresearcher

# 3. Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate

# 4. Установка ядра и PyObjC (критично для pywebview на Mac)
pip install pyobjc-framework-WebKit pyobjc-core
pip install -r requirements.txt

# 5. Установка браузеров Playwright
playwright install chromium

# 6. Запуск сервера и интерфейса
python3 install_all.py
python3 run_scraper.py
```

### Настройка Claude Code (Опционально)
Если вы используете `Сlaude Code`, находясь в директории `virealresearcher`, введите команду:
```bash
/banana-install
```
Claude Code сам произведет инъекцию MCP-сервера в `~/.claude.json`.
Для запусков парсера из любой точки в системе:
```bash
/banana-run
```
