# Железобетонная Установка: macOS (Apple Silicon / Intel)

Вставьте скрипт в **Terminal.app** или **iTerm2**.

## Автоматическая установка

```bash
# 1. Установка инструментов Xcode (если не установлены)
xcode-select --install || true

# 2. Клонировать репозиторий
git clone https://github.com/fsbtactic-code/virealresearcher.git
cd virealresearcher

# 3. Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 4. Установить все зависимости (pywebview, playwright, sentence-transformers и др.)
pip install -r requirements.txt

# 5. Финальная настройка (Playwright Chromium + проверка импортов)
python3 install_all.py

# 6. Авторизация Instagram (один раз — сохраняет сессию)
python3 auth.py

# 7. Запуск парсера
python3 run_scraper.py
```

> ⚠️ **Шаг 6 обязателен перед первым запуском.** Откроется браузер — войдите в Instagram вручную. После закрытия браузера сессия сохранится автоматически.

## Настройка Claude Code (опционально)

Если используете **Claude Code**, находясь в папке `virealresearcher`:

```bash
/banana-install
```

Claude Code сам выполнит установку и зарегистрирует MCP. Для запуска парсера из любого места:

```bash
/banana-run
```

## Если что-то пошло не так

| Ошибка | Решение |
|--------|---------|
| `storage_state.json not found` | Запустите `python3 auth.py` |
| `playwright` ошибки | `python3 -m playwright install chromium` |
| WebView не открывается | `pip install pyobjc-framework-WebKit pyobjc-core` |
| Медленная загрузка AI-модели | Первый запуск — модель (~118 МБ) скачается один раз |
| Модуль не найден | `pip install -r requirements.txt` |
