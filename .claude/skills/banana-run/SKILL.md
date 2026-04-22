---
description: Запуск Banana Parser (парсер + дашборд)
---
Запусти главное окно Banana Parser:

1. Проверь что зависимости установлены: `python -c "import webview, playwright; print('OK')"` (Mac: `python3 -c ...`)
2. Если нет — сначала запусти `/banana-install`
3. ЗАПУСК ИНТЕРФЕЙСА: Получи жёсткий путь, который был сохранён при установке:
   - Mac/Linux: `cat ~/.banana_parser_path`
   - Windows: `type $env:USERPROFILE\.banana_parser_path`
   Это и есть АБСОЛЮТНЫЙ ПУТЬ к папке парсера. Если файла нет — запусти `/banana-install`.
4. Запусти парсер в ОТДЕЛЬНОМ окне:
   - **macOS**: `osascript -e 'tell app "Terminal" to do script "cd <ПУТЬ> && python3 run_scraper.py"'`
   - **Windows**: `cmd /c start python <АБСОЛЮТНЫЙ_ПУТЬ>\run_scraper.py`
   ОБЯЗАТЕЛЬНО сделай это сам!
5. Сообщи пользователю что окно открыто и готово к работе.
