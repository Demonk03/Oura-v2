# Design: Мультипользовательская архитектура (Supabase)

**Дата:** 2026-03-27
**Проект:** Oura-v2
**Статус:** Approved

---

## Контекст

Существующий проект (`Oura/`) — однопользовательский: CSV как хранилище, секреты в GitHub, данные коммитятся в репозиторий. Новый проект (`Oura-v2/`) — параллельная реализация с продакшн-архитектурой для до 5 пользователей. Старый проект остаётся как есть и не затрагивается.

---

## Цель

Поддержать до 5 независимых пользователей с изолированными данными, самостоятельной регистрацией через Telegram и сохранением всей бизнес-логики (алерты, weekly-отчёты, GPT-анализ) без изменений.

---

## Выбранный подход: Вариант 2

Supabase как БД + Telegram-бот для регистрации + GitHub Actions для сбора данных и уведомлений.

---

## Схема базы данных (Supabase / PostgreSQL)

### Таблица `users`
```sql
CREATE TABLE users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id  BIGINT UNIQUE NOT NULL,
  oura_pat     TEXT NOT NULL,
  timezone     TEXT NOT NULL DEFAULT 'Europe/Moscow',
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Таблица `health_logs`
```sql
CREATE TABLE health_logs (
  id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  date    DATE NOT NULL,

  -- daily_readiness
  readiness_score                    INT,
  readiness_activity_balance_score   INT,
  readiness_body_temp_score          INT,
  readiness_hrv_balance_score        INT,
  readiness_prev_day_score           INT,
  readiness_prev_night_score         INT,
  readiness_recovery_score           INT,
  readiness_resting_hr_score         INT,
  readiness_sleep_balance_score      INT,
  temperature_deviation              FLOAT,
  temperature_trend_deviation        FLOAT,

  -- daily_sleep
  sleep_score              INT,
  sleep_deep_score         INT,
  sleep_efficiency_score   INT,
  sleep_latency_score      INT,
  sleep_rem_score          INT,
  sleep_restfulness_score  INT,
  sleep_timing_score       INT,
  sleep_total_score        INT,

  -- daily_activity
  activity_score               INT,
  activity_meet_targets_score  INT,
  activity_move_hour_score     INT,
  activity_recovery_score      INT,
  activity_stay_active_score   INT,
  activity_train_freq_score    INT,
  activity_train_vol_score     INT,
  steps                        INT,
  active_calories              INT,
  total_calories               INT,
  walking_distance             INT,
  high_activity_time           INT,
  sedentary_time               INT,

  -- daily_resilience
  resilience_level          TEXT,
  resilience_sleep_score    INT,
  resilience_daytime_score  INT,
  resilience_stress_score   INT,

  -- daily_stress
  stress_high    INT,
  recovery_high  INT,
  day_summary    TEXT,

  -- sleep (детальные)
  average_heart_rate     FLOAT,
  lowest_heart_rate      INT,
  average_hrv            FLOAT,
  average_breath         FLOAT,
  efficiency             INT,
  latency                INT,
  time_in_bed            INT,
  total_sleep_duration   INT,
  awake_time             INT,
  light_sleep_duration   INT,
  deep_sleep_duration    INT,
  rem_sleep_duration     INT,
  nap_count              INT,
  nap_duration           INT,

  -- daily_spo2
  spo2_average               FLOAT,
  breathing_disturbance_index INT,

  -- enhanced_tag
  tags TEXT,

  -- workout
  workout_count     INT,
  workout_types     TEXT,
  workout_calories  INT,
  workout_distance  INT,
  workout_duration  INT,

  UNIQUE(user_id, date)
);
```

### Таблица `weekly_summaries`
```sql
CREATE TABLE weekly_summaries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  week_start      DATE NOT NULL,
  weekly_data     JSONB,
  weekly_history  JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, week_start)
);
```

---

## Регистрация пользователя (Telegram-бот)

**Флоу:**
1. Пользователь пишет боту: `/register <oura_token>`
2. Бот делает тестовый вызов Oura API с этим токеном
3. Если токен невалиден → отвечает с ошибкой
4. Если токен валиден → `INSERT INTO users (telegram_id, oura_pat)` → подтверждение

**Команды бота:**
- `/register <oura_token>` — регистрация
- `/status` — последние данные пользователя
- `/stop` — деактивация (`is_active = false`)

**Хостинг:** `bot.py` как webhook на Render.com (free tier). Telegram отправляет POST на публичный URL при каждом сообщении.

---

## Сбор данных (GitHub Actions)

**update.yml — изменения:**
- Читает активных пользователей из Supabase: `SELECT * FROM users WHERE is_active = true`
- Итерируется по каждому: берёт `oura_pat`, запрашивает Oura API, пишет в `health_logs` через `UPSERT`
- Коммит в git не нужен — данные живут в БД

**Секреты GitHub (общие для всех пользователей):**
```
SUPABASE_URL       — URL проекта Supabase
SUPABASE_KEY       — service_role key
OPENAI_API_KEY     — ключ OpenAI
TG_TOKEN           — токен Telegram-бота
```

Oura PAT каждого пользователя хранится в `users.oura_pat` в Supabase, не в GitHub Secrets.

---

## Алерты и еженедельный отчёт

Логика (`alert_checker.py`, `gpt_table_analyzer.py`) не меняется. Меняется только:
- Источник данных: `health_logs WHERE user_id = X` вместо CSV
- Получатель: `users.telegram_id` вместо `TG_MY_ID` из env

**alert_check.yml:**
```
iterate active users
  → load health_logs (30 days) for user
  → check_alerts(df)              ← та же логика
  → if alerts: GPT → sendMessage(telegram_id)
```

**send_telegram_weekly.yml:**
```
iterate active users
  → load weekly_summaries for user
  → gpt_table_analyzer(weekly_data, weekly_history)
  → sendMessage(telegram_id)
```

---

## Итоговая архитектура

```
┌─────────────────────────────────────────────────────┐
│                    Supabase (БД)                     │
│  users: telegram_id, oura_pat, timezone, is_active  │
│  health_logs: user_id, date, 53 поля                │
│  weekly_summaries: user_id, week_start, jsonb        │
└──────────────┬──────────────────────────────────────┘
               │
    ┌──────────┴──────────┬──────────────────┐
    │                     │                  │
┌───▼────────┐    ┌───────▼──────┐   ┌───────▼──────┐
│  bot.py    │    │  update.yml  │   │alert_check / │
│ (Render)   │    │  7:00 UTC    │   │weekly.yml    │
│            │    │  ежедневно   │   │              │
│/register   │    │              │   │              │
│→ валидация │    │iterate users │   │iterate users │
│→ INSERT    │    │→ Oura API    │   │→ Supabase    │
│  users     │    │→ UPSERT      │   │→ GPT         │
│            │    │  health_logs │   │→ Telegram    │
└────────────┘    └──────────────┘   └──────────────┘
```

---

## Структура файлов Oura-v2

```
Oura-v2/
├── bot.py                          # Telegram-бот (регистрация)
├── update_missing_dates.py         # Сбор данных → Supabase
├── alert_checker.py                # Алерты → Supabase → Telegram
├── gpt_table_analyzer.py           # GPT weekly-анализ
├── send_telegram_message.py        # Отправка weekly-отчёта
├── db.py                           # Общий модуль для работы с Supabase
├── requirements.txt
├── .env                            # Локальные переменные (не в git)
├── .github/workflows/
│   ├── update.yml
│   ├── alert_check.yml
│   └── send_telegram_weekly.yml
└── docs/superpowers/specs/
    └── 2026-03-27-multiuser-supabase-design.md
```

**Новый модуль `db.py`** — единая точка работы с Supabase: подключение, get_active_users(), upsert_health_log(), get_health_logs(user_id, days), get_weekly_summary(), upsert_weekly_summary().

---

## Что не меняется

- Логика детекции алертов (9 паттернов)
- GPT-промпты
- Структура полей данных Oura (53 поля)
- Расписание GitHub Actions
- Python как основной язык

---

## Ограничения

- Supabase free tier: 500MB хранилища, 2GB трафика/месяц — достаточно для 5 пользователей
- Render.com free tier: бот засыпает после 15 минут неактивности, просыпается при входящем сообщении (задержка ~30 сек на первое сообщение)
- GitHub Actions остаётся вычислительным слоем — не переезжаем на serverless
