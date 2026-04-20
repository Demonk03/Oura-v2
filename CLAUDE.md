# Oura-v2 — Project Context

## Obsidian-заметка
`/Users/dkossenkov/Documents/Private files/Second brain/Private_projects/Oura v2.md`

---

## Что это

Личный health-трекер. Собирает данные с кольца Oura Ring через API, хранит в Supabase (PostgreSQL), отправляет алерты и weekly-дайджест в Telegram через GPT-анализ. Фронтенд — статичный дашборд на GitHub Pages.

Поддерживает до 5 независимых пользователей. Регистрация — через Telegram-бот.

---

## Архитектура

```
Oura API → update_missing_dates.py (GitHub Actions) → Supabase (health_logs)
                                                              ↓
                                          alert_checker.py (GitHub Actions) → Telegram
                                          send_telegram_message.py (GitHub Actions) → Telegram
                                                              ↓
                                          bot.py (Flask, Render) → API proxy → GitHub Pages (дашборд)
```

### Компоненты

| Файл | Назначение |
|---|---|
| `bot.py` | Flask-сервер: Telegram webhook + API proxy для дашборда + /auth/telegram |
| `db.py` | Все обращения к Supabase (users, health_logs, weekly_summaries) |
| `update_missing_dates.py` | Сбор данных за пропущенные даты для всех активных пользователей |
| `alert_checker.py` | Проверка алертов + GPT-анализ + отправка в Telegram |
| `send_telegram_message.py` | Weekly-дайджест через GPT → Telegram |
| `gpt_table_analyzer.py` | Форматирование данных для GPT weekly-анализа |
| `docs/` | Фронтенд дашборда (index.html, login.html, dashboard.js, dashboard.css, config.js) |

### Внешние сервисы

| Сервис | Роль |
|---|---|
| Supabase | PostgreSQL: users, health_logs, weekly_summaries |
| Render.com | Хостинг Flask-бота (`https://oura-v2.onrender.com`) |
| GitHub Pages | Дашборд (`https://demonk03.github.io/Oura-v2/`) |
| GitHub Actions | Расписание: сбор данных, алерты, weekly |
| OpenAI GPT-4 | Текст алертов и weekly-дайджестов |
| Telegram | Бот `@good_morning_oura_bot` |

---

## База данных (Supabase)

### Таблица `users`
- `id` UUID PK
- `telegram_id` BIGINT UNIQUE
- `oura_pat` TEXT
- `timezone` TEXT (default `Europe/Moscow`)
- `is_active` BOOLEAN

### Таблица `health_logs`
- Одна строка = один день для одного пользователя
- UNIQUE(user_id, date) — upsert-безопасна
- Поля: readiness/sleep/activity/stress/resilience scores + детальные метрики сна (HRV, HR, stages) + SpO2 + теги + тренировки
- `activity_score` IS NULL используется как маркер неполной записи (см. Особенности API)

### Таблица `weekly_summaries`
- `weekly_data` JSONB — данные текущей недели
- `weekly_history` JSONB — история предыдущих недель
- UNIQUE(user_id, week_start)

---

## GitHub Actions

| Файл | Расписание | Скрипт |
|---|---|---|
| `update.yml` | `0 7 * * *` (07:00 UTC) | `update_missing_dates.py` |
| `alert_check.yml` | `30 7 * * *` (07:30 UTC) | `alert_checker.py` |
| `send_telegram_weekly.yml` | `0 21 * * 0` (21:00 UTC воскресенье) | `send_telegram_message.py` |

Все запускаются через `workflow_dispatch` вручную.

Secrets в репозитории: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`, `TG_TOKEN`.

---

## Авторизация дашборда

```
1. login.html → Telegram Login Widget
2. Telegram → POST /auth/telegram (Render)
3. bot.py проверяет HMAC-SHA256 подпись через TG_TOKEN
4. Ищет пользователя по telegram_id в Supabase
5. Генерирует JWT (HS256, APP_SECRET, срок 7 дней)
6. JWT в localStorage → запросы к /api/logs и /api/weekly
7. bot.py декодирует JWT → достаёт user_id → запрашивает Supabase с service_role ключом
```

Прямой доступ фронтенда к Supabase невозможен: Supabase использует ES256, приватный ключ у них. Решение — API proxy через Render.

**CORS:** `DASHBOARD_ORIGIN` env var (default `https://demonk03.github.io`).

---

## Telegram-бот: команды

| Команда | Действие |
|---|---|
| `/start` | Приветствие. Если не зарегистрирован — показывает inline-кнопку для получения токена |
| `/register <token>` | Регистрация или реактивация. Валидирует токен через Oura API (`/personal_info`) |
| `/status` | Последняя запись из health_logs (readiness, sleep, HRV, HR) |
| `/stop` | Деактивация (is_active = False) |

---

## Известные особенности Oura API

**`daily_activity` и `sleep` — exclusive `end_date`**

Оба эндпоинта с эксклюзивным `end_date`. При `start_date == end_date` возвращают 0 записей.
Фикс: в `update_missing_dates.py` для обоих эндпоинтов `end_date = date + 1 day` (переменная `next_day`).
`get_missing_dates` включает даты с `activity_score IS NULL` — позволяет перезалить неполные записи.

**`daily_stress` — секунды, не минуты**

`stress_high` и `recovery_high` приходят в секундах. В Supabase хранятся as-is.
Конвертация → минуты только на фронте: функция `secToMin` в `dashboard.js`.

---

## Переменные окружения

| Переменная | Где нужна |
|---|---|
| `SUPABASE_URL` | Все скрипты, bot.py |
| `SUPABASE_KEY` | Все скрипты, bot.py (service_role key `sb_secret_...`) |
| `TG_TOKEN` | bot.py, alert_checker.py, send_telegram_message.py |
| `OPENAI_API_KEY` | alert_checker.py, send_telegram_message.py |
| `APP_SECRET` | bot.py — подпись JWT дашборда (32 байта hex) |
| `DASHBOARD_ORIGIN` | bot.py — CORS origin (default: `https://demonk03.github.io`) |

Генерация APP_SECRET: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## Алерты (alert_checker.py)

Правила срабатывания:
- `readiness_low` — readiness < 70
- `sleep_crash` — sleep score < 60
- `temperature_spike` — отклонение температуры > ±0.3°C
- `sleep_trend_down` — sleep score ниже медианы 30 дней, 5 дней подряд
- `sleep_duration_trend` — длительность сна ниже нормы 5 дней подряд
- `rem_trend_down` — REM ниже нормы 5 дней подряд
- `hr_elevated` — ночной пульс выше нормы на 3+ уд/мин, 3 ночи подряд
- `stress_balance_worsening` — баланс stress/recovery ухудшился на 15%+ за 2 недели
- `hrv_trend_down` — HRV ниже нормы на 10%+ за 14 дней

Базовая линия = медиана за последние 30 дней. При срабатывании — GPT-4 формирует текст, отправляется в Telegram.

---

## Render.com

- Build: `pip install -r requirements.txt`
- Start: `python3 bot.py`
- Auto-deploy может не срабатывать — при необходимости ручной деплой через dashboard.

После деплоя или смены токена зарегистрировать webhook:
```bash
curl "https://api.telegram.org/bot<TG_TOKEN>/setWebhook?url=https://oura-v2.onrender.com/webhook"
```

---

## Локальная разработка

`.env` (не коммитится):
```
SUPABASE_URL=...
SUPABASE_KEY=...
OPENAI_API_KEY=...
TG_TOKEN=...
APP_SECRET=...
```

```bash
python3 update_missing_dates.py   # ручной сбор данных
python3 bot.py                    # запуск бота локально (webhook не работает без публичного URL)
```

---

## Статус реализации

Всё реализовано. Планы из `docs/superpowers/plans/` выполнены по состоянию на 2026-03-29:
- Мультипользовательская архитектура (Supabase)
- Онбординг бота (/start с inline-кнопкой)
- Дашборд (login + index + CSS + JS)
- API proxy (Flask на Render вместо прямого Supabase)
- Фикс activity_score (exclusive end_date)
- Фикс stress в секундах (конвертация на фронте)
- Фикс alert_check workflow
