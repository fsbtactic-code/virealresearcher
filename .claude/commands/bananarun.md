---
description: Запуск парсера (поиск и дашборд)
---
Запусти главное окно Banana Parser:

1. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"`
2. Если нет — сначала запусти `/banana-install`
3. Запусти парсер в ОТДЕЛЬНОМ окне: `cmd /c start python run_scraper.py` (Windows) или `osascript -e 'tell app "Terminal" to do script "python run_scraper.py"'` (Mac). ОБЯЗАТЕЛЬНО сделай это сам!
4. Сообщи пользователю что окно открыто и готово к работе, и теперь терминал Клода снова свободен!
