---
description: Установка Banana Parser и зависимостей
---
Установи Banana Parser и подготовь к работе:

1. Проверь что Python 3.10+ установлен, если нет — установи
2. Запусти `python install_all.py` — он сам установит все зависимости и Playwright
3. Если install_all.py выдал ошибки — исправь их:
   - pip не найден → `python -m ensurepip --upgrade`
   - playwright fails → `python -m playwright install chromium`
   - Любые другие → прочитай `.ai-context.md` и исправь
4. Проверь что всё работает: `python -c "from skills import master_viral_hunter; print('OK')"`
5. Если `storage_state.json` не существует — запусти команду `/bananaauth` чтобы открыть окно для входа в Instagram.
6. Сообщи что окно для входа в Instagram было открыто (или что оно не требуется), и скажи пользователю запустить `/bananarun` после успешного входа в запасной аккаунт.
