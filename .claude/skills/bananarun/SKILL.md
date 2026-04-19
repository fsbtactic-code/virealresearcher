---
description: Запуск парсера (поиск и дашборд)
---
Запусти главное окно Banana Parser:

1. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"`
2. Если нет — сначала запусти `/banana-install`
3. ЗАПУСК ИНТЕРФЕЙСА: Сначала найди на диске папку, где лежит `run_scraper.py` (вероятно `virealresearcher`). Затем перейди в неё `cd <путь>` ИЛИ используй абсолютный путь к файлу.
4. Запусти парсер в ОТДЕЛЬНОМ окне: `cmd /c start python <АБСОЛЮТНЫЙ_ПУТЬ>/run_scraper.py` (Windows) или `osascript -e 'tell app "Terminal" to do script "cd <ПУТЬ> && python run_scraper.py"'` (Mac). ОБЯЗАТЕЛЬНО сделай это сам!
5. Сообщи пользователю что окно открыто и готово к работе, и теперь терминал Клода свободнее!
