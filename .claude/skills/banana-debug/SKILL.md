---
description: Диагностика и автоматический самодебаг Banana Parser
---
Выполни полную автодиагностику Banana Parser и исправь все найденные проблемы:

## ШАГ 1: Прочитай архитектуру
Прочитай `.ai-context.md` в папке проекта. Найди путь через `~/.Banana Parser_path` (Mac: `cat ~/.Banana Parser_path`, Win: `type $env:USERPROFILE\.Banana Parser_path`).

## ШАГ 2: Проверь все импорты
```
python3 -c "
import sys
mods = ['playwright.async_api', 'playwright_stealth', 'webview', 'pydantic', 'mcp']
for m in mods:
    try:
        __import__(m)
        print(f'  ✅ {m}')
    except ImportError as e:
        print(f'  ❌ {m}: {e}')
"
```
Если что-то ❌ — выполни `pip install -r requirements.txt` в папке проекта.

## ШАГ 3: Проверь Playwright
```
python3 -m playwright install chromium
```
Затем:
```
python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop(); print('Playwright OK')"
```

## ШАГ 4: Проверь storage_state.json
Если файла нет — ПРЕДУПРЕДИ пользователя: "Нет активной сессии Instagram. Нужно запустить `/banana-auth`". Не запускай парсер без него.

## ШАГ 5: Проверь MCP сервер
```
python3 -c "
import sys, os
from pathlib import Path
sys.path.insert(0, '.')
try:
    import mcp_server
    print('MCP server: OK')
except Exception as e:
    print(f'MCP server ERROR: {e}')
"
```
Если ошибка — прочитай `scraper.log` и исправь.

## ШАГ 6: Проверь конфиг Claude
Найди `~/.claude.json` и убедись что есть блок:
```json
"Banana Parser": {
  "command": "python3",
  "args": ["/PATH/TO/mcp_server.py"],
  "cwd": "/PATH/TO/Banana Parser"
}
```
Если нет — добавь, используя реальный путь из `~/.Banana Parser_path`.

## ШАГ 7: Запусти тест
```
python3 -c "
import asyncio, sys
sys.path.insert(0, '.')
from interceptor import PostFilter, InterceptorState
f = PostFilter(min_likes=0)
s = InterceptorState()
print(f'PostFilter: OK, InterceptorState: OK')
"
```

## ШАГ 8: Отчёт
Выведи пользователю чёткий список:
- ✅ что работает
- ❌ что сломано + команду для исправления
- Если нашёл и исправил баги в коде — объясни что именно изменил.

**Правило**: Если что-то сломано — НЕ ОСТАНАВЛИВАЙСЯ. Исправь сам и сообщи что сделал. Читай `.ai-context.md` для понимания архитектуры перед любыми изменениями кода.
