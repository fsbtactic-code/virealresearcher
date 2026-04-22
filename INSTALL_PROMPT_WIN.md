# Железобетонная Установка: Windows

Скопируйте блок в **PowerShell** (запуск от имени Администратора не обязателен).

## Автоматическая установка

```powershell
# 1. Клонировать репозиторий
git clone https://github.com/fsbtactic-code/virealresearcher.git
cd virealresearcher

# 2. Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# 3. Установить все зависимости (pywebview, playwright, sentence-transformers и др.)
pip install -r requirements.txt

# 4. Финальная настройка (Playwright Chromium + проверка импортов)
python install_all.py

# 5. Авторизация Instagram (один раз — сохраняет сессию)
python auth.py

# 6. Запуск парсера
python run_scraper.py
```

> ⚠️ **Шаг 5 обязателен перед первым запуском.** Откроется браузер — войдите в Instagram вручную. После закрытия браузера сессия сохранится автоматически.

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
| `storage_state.json not found` | Запустите `python auth.py` |
| `playwright` ошибки | `python -m playwright install chromium` |
| Медленная загрузка AI-модели | Первый запуск — модель (~118 МБ) скачается один раз |
| Модуль не найден | `pip install -r requirements.txt` |
