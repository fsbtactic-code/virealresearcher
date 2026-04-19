---
description: Авторизация в Instagram
---
Запусти графическое окно авторизации Instagram:

1. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"`
2. Запусти окно авторизации в ОТДЕЛЬНОМ процессе: `cmd /c start python auth.py` (Windows) или `osascript -e 'tell app "Terminal" to do script "python auth.py"'` (Mac). ОБЯЗАТЕЛЬНО сделай это сам!
3. Сообщи пользователю, чтобы он залогинился в Instagram, и когда закончит, окно закроется автоматически. После этого нужно написать `/bananarun` для старта парсера.
