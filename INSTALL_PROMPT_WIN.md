# Железобетонная Установка: Windows

Скопируйте этот Markdown-текст и отправьте в Claude Code или любую другую консоль, поддерживающую Markdown-установку, либо просто выполните команды в PowerShell по очереди.

## Автоматическая настройка (PowerShell)

Запустите PowerShell **от имени Администратора** и выполните один длинный скрипт:

```powershell
# 1. Скачивание репозитория
git clone https://github.com/fsbtactic-code/virealresearcher.git
cd virealresearcher

# 2. Создание виртуального окружения
python -m venv .venv
.venv\Scripts\activate

# 3. Установка ядра и зависимостей (включая Playwright)
pip install -r requirements.txt
python install_all.py

# 4. Первый запуск интерфейса (сгенерирует session files)
python run_scraper.py
```

### Настройка Claude Code (Опционально)
Если вы используете `Сlaude Code`, находясь в директории `virealresearcher`, введите команду:
```bash
/banana-install
```
Claude Code сам произведет инъекцию навыков в ваш `~/.claude.json` и выведет статус `[ OK ]`.
Вызов окна парсинга из любого места в ОС:
```bash
/banana-run
```
