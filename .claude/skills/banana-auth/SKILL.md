---
description: Авторизация в Instagram через Banana Parser
---
Запусти графическое окно авторизации Instagram:

1. ПЕРЕД ЗАПУСКОМ выведи пользователю в чат БОЛЬШОЕ ПРЕДУПРЕЖДЕНИЕ: "⚠️ ВНИМАНИЕ: Используйте ТОЛЬКО ЗАПАСНОЙ аккаунт Instagram (фейк)! Использование основного личного аккаунта может привести к его блокировке!"
2. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"` (Mac: `python3 -c ...`)
3. Найди `auth.py`. Он находится по жёсткому пути, который сохранён в файле `~/.banana_parser_path`. Прочитай этот файл (`cat ~/.banana_parser_path` на Mac/Linux, `type $env:USERPROFILE\.banana_parser_path` на Windows). Если файла нет — нужно запустить `/banana-install`.
4. Запусти окно авторизации в ОТДЕЛЬНОМ процессе:
   - **macOS**: `osascript -e 'tell app "Terminal" to do script "cd <ПУТЬ> && python3 auth.py"'`
   - **Windows**: `cmd /c start python <АБСОЛЮТНЫЙ_ПУТЬ>\auth.py`
   ОБЯЗАТЕЛЬНО запусти это самостоятельно!
5. Сообщи пользователю, чтобы он залогинился в Instagram. Когда закончит — окно закроется. После этого написать `/banana-run` для старта парсера.
