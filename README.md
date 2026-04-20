# Banana Parser — Stealth Архитектура Перехвата GraphQL (v3.1)

**Репозиторий:** [https://github.com/fsbtactic-code/virealresearcher](https://github.com/fsbtactic-code/virealresearcher)

Banana Parser — это профессиональный инструмент для скрытого скрапинга и анализа Instagram профилей, Reels, Каруселей и хэштегов. Главная особенность: полный отказ от парсинга HTML DOM. Инструмент перехватывает GraphQL и JSON трафик на уровне сети через `playwright` stealth mode, что сводит вероятность блокировок профиля к минимуму и многократно ускоряет отдачу данных.

## Возможности

- **Пассивный сетевой перехват**: Прямой перехват запросов (XHR/Fetch) к API Instagram (без `<div class="...">` и BeautifulSoup).
- **Stealth-инъекции**: Поддержка `playwright-stealth` для имитации живого браузера. Совершенно прозрачная работа с UI Instagram.
- **Интеграция Claude MCP**: Нативная интеграция навыков Claude Code. Управление скриптом прямо из IDE как через MCP Server.
- **Аналитика Виральности**: Оценка Velocity Score (лайков/ч) и фильтрация нулевого вовлечения.
- **UI на базе Webview**: Интерфейс на Liquid Glass (CSS/JS) встроенный прямо в Python-процесс через `pywebview`. Отвязан от системных браузеров.
- **Автоматический парсинг Subtitles**: Резервная система Whisper для "немых" Reels (поддержка AI-классификации).

## Установка

Вы можете найти подробнейшие "железобетонные" bash/powershell-команды в соответствующих файлах:
- Для ОС Windows: `INSTALL_PROMPT_WIN.md`
- Для ОС macOS / Linux: `INSTALL_PROMPT_MACOS.md`

### Быстрый запуск

```bash
git clone https://github.com/fsbtactic-code/virealresearcher.git
cd virealresearcher
python -m venv .venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
python install_all.py
```

## Работа через Claude Code

Пакет поставляется с `.claude/skills/` обвязкой:

1. Перейдите в корневую папку репозитория.
2. Введите `/banana-install`. Claude самостоятельно настроит среду и зарегистрирует инструменты в `~/.claude.json`.
3. Для авторизации Instagram: `/banana-auth`.
4. Для запуска GUI: `/banana-run`.

## Основные Файлы Архитектуры

* `interceptor.py` — Ядро перехвата GraphQL/XHR трафика.
* `run_scraper.py` — Главный воркер и API-мост для UI.
* `mcp_server.py` — stdio сервер для интеграции Banana Parser в Claude Desktop.
* `ui_generator.py` — Генератор интерактивных HTML-отчетов.

Подробная архитектура описана в файле `.ai-context.md`.

## Лицензия

Утилита предназначена исключительно для маркетингового анализа и конкурентной разведки в рамках открытых данных. Разработчики не несут ответственности при блокировке аккаунта Instagram со стороны Meta.
