---
description: Установка Banana Parser и зависимостей
---
Установи Banana Parser и подготовь к работе:

1. Проверь наличие Python 3.10+. Если нет — дай инструкцию по установке.
2. Проверь наличие папки с парсером (только в `./virealresearcher`, `../virealresearcher`, `~/virealresearcher` и `~/Documents/Банан/competitor parser`. ЗАПРЕЩАЕТСЯ делать долгий глобальный `find`!). Если её нет (или нет `install_all.py`), выполни `git clone https://github.com/fsbtactic-code/virealresearcher.git`. Если есть — зайди и сделай `git pull`. Запомни АБСОЛЮТНЫЙ ПУТЬ к ней.
3. Скопируй (с перезаписью) все скиллы из папки `virealresearcher/.claude/skills/` в папку `.claude/skills/` ТЕКУЩЕГО ПРОЕКТА (откуда ты вызван).
4. Обнови `settings.json` текущего проекта: явно включи скопированные скиллы в `skillOverrides`, и добавь `Bash(*)` в `permissions.allow`.
5. Найди глобальный файл конфигурации Claude (`~/.claude.json` или `%APPDATA%\Claude\claude_desktop_config.json`). Пропиши туда наш MCP-сервер: ключ `"banana-parser"` внутри `mcpServers`, с указанием АБСОЛЮТНОГО ПУТИ к `mcp_server.py` в поле `args` и абсолютного пути к папке в `cwd`.
6. Перейди в папку `virealresearcher` и запусти `python install_all.py`.
7. Если `install_all.py` выдал ошибки:
   - "pip not found" → `python -m ensurepip --upgrade`
   - "playwright fails" → `python -m playwright install chromium`
   - Остальные → изучи `virealresearcher/.ai-context.md`.
8. После успешной установки попроси пользователя запустить `/bananaauth` для авторизации в запасном аккаунте Instagram, либо запусти сразу `/bananarun`, если сессия уже есть.
