---
description: Авторизация в Instagram
---
Запусти графическое окно авторизации Instagram:

1. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"`
2. Найди `auth.py`. Проверь текущую папку, `../virealresearcher`, `~/virealresearcher` и `~/Documents/Банан/competitor parser`. **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО делать глобальный `find` по всему диску (он виснет)!** Если не нашел мгновенно — просто спроси путь у пользователя.
3. Запусти окно авторизации в ОТДЕЛЬНОМ процессе: `cmd /c start python <АБСОЛЮТНЫЙ_ПУТЬ>/auth.py` (Windows) или `osascript -e 'tell app "Terminal" to do script "cd <ПУТЬ> && python auth.py"'` (Mac). ОБЯЗАТЕЛЬНО сделай это сам!
4. Сообщи пользователю, чтобы он залогинился в Instagram, и когда закончит, окно закроется автоматически. После этого нужно написать `/bananarun` для старта парсера.
