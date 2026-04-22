---
description: Установка Banana Parser и всех зависимостей
---
Установи Banana Parser и подготовь к работе:

1. Проверь наличие Python 3.10+. Если нет — дай инструкцию по установке.
2. Проверь наличие папки с парсером (только в `./Banana Parser`, `../Banana Parser`, `~/Banana Parser`, `~/banana-parser`, `./virealresearcher`, `../virealresearcher`. ЗАПРЕЩАЕТСЯ делать долгий глобальный `find`!). Если её нет (или нет `install_all.py`), выполни `git clone https://github.com/fsbtactic-code/virealresearcher.git Banana Parser`. Если есть — зайди и сделай `git pull`. Запомни АБСОЛЮТНЫЙ ПУТЬ к ней.
3. Скопируй (с перезаписью) все скиллы из папки `Banana Parser/.claude/skills/` в папку `.claude/skills/` ТЕКУЩЕГО ПРОЕКТА (откуда ты вызван).
4. Обнови `settings.json` текущего проекта: явно включи скопированные скиллы в `skillOverrides`, и добавь `Bash(*)` в `permissions.allow`.
5. Найди глобальный файл конфигурации Claude (`~/.claude.json` на Mac/Linux или `%APPDATA%\Claude\claude_desktop_config.json` на Windows). Пропиши туда наш MCP-сервер: ключ `"Banana Parser"` внутри `mcpServers`, с указанием АБСОЛЮТНОГО ПУТИ к `mcp_server.py` в поле `args` и абсолютного пути к папке в `cwd`. Пример:
   ```json
   "Banana Parser": {
     "command": "python3",
     "args": ["/ABSOLUTE/PATH/TO/mcp_server.py"],
     "cwd": "/ABSOLUTE/PATH/TO/Banana Parser"
   }
   ```
   На Windows используй `"python"` вместо `"python3"`.
6. Перейди в папку проекта и запусти `python install_all.py` (или `python3 install_all.py` на macOS).
7. Если `install_all.py` выдал ошибки:
   - "pip not found" → `python -m ensurepip --upgrade`
   - "playwright fails" → `python -m playwright install chromium`
   - macOS "WebView" ошибка → `pip install pyobjc-framework-WebKit pyobjc-core`
   - macOS "xcode-select" -> запусти `xcode-select --install` и подожди установки
   - Остальные → запусти `/banana-debug`
8. После успешной установки предложи пользователю запустить `/banana-auth` для авторизации Instagram, либо `/banana-run`, если сессия уже есть.
