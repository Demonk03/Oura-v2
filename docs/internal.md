# Internal Documentation

Operational reference for setting up and maintaining Oura-v2.

---

## Services

| Service | Purpose | URL |
|---|---|---|
| Supabase | PostgreSQL database | Project URL in `.env` as `SUPABASE_URL` |
| Render.com | Bot + API hosting | `https://oura-v2.onrender.com` |
| GitHub Pages | Dashboard frontend | `https://demonk03.github.io/Oura-v2/` |
| Telegram | Bot delivery | `@good_morning_oura_bot` |
| GitHub Actions | Scheduled automation | `Demonk03/Oura-v2` |
| OpenAI | GPT analysis | Key in `.env` as `OPENAI_API_KEY` |

---

## Database Schema (Supabase)

### users
```sql
CREATE TABLE users (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id            BIGINT UNIQUE NOT NULL,
  oura_pat               TEXT NOT NULL,
  timezone               TEXT NOT NULL DEFAULT 'Europe/Moscow',
  is_active              BOOLEAN NOT NULL DEFAULT TRUE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Fitbit / Google Health, добавлено 27.10.2026
  google_refresh_token   TEXT,
  google_health_user_id  TEXT,
  source                 TEXT NOT NULL DEFAULT 'oura'
);
```

`google_refresh_token` хранится здесь, а не в секретах GitHub: токен привязан
к пользователю, а не к инсталляции. В секретах лежат только `GOOGLE_CLIENT_ID`
и `GOOGLE_CLIENT_SECRET`.

### health_logs
```sql
CREATE TABLE health_logs (
  id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  date    DATE NOT NULL,

  -- daily_readiness
  readiness_score INT, readiness_activity_balance_score INT,
  readiness_body_temp_score INT, readiness_hrv_balance_score INT,
  readiness_prev_day_score INT, readiness_prev_night_score INT,
  readiness_recovery_score INT, readiness_resting_hr_score INT,
  readiness_sleep_balance_score INT,
  temperature_deviation FLOAT, temperature_trend_deviation FLOAT,

  -- daily_sleep
  sleep_score INT, sleep_deep_score INT, sleep_efficiency_score INT,
  sleep_latency_score INT, sleep_rem_score INT,
  sleep_restfulness_score INT, sleep_timing_score INT, sleep_total_score INT,

  -- daily_activity
  activity_score INT, activity_meet_targets_score INT,
  activity_move_hour_score INT, activity_recovery_score INT,
  activity_stay_active_score INT, activity_train_freq_score INT,
  activity_train_vol_score INT,
  steps INT, active_calories INT, total_calories INT,
  walking_distance INT, high_activity_time INT, sedentary_time INT,

  -- daily_resilience
  resilience_level TEXT,
  resilience_sleep_score INT, resilience_daytime_score INT, resilience_stress_score INT,

  -- daily_stress
  stress_high INT, recovery_high INT, day_summary TEXT,

  -- sleep (detailed)
  average_heart_rate FLOAT, lowest_heart_rate INT,
  average_hrv FLOAT, average_breath FLOAT,
  efficiency INT, latency INT, time_in_bed INT,
  total_sleep_duration INT, awake_time INT,
  light_sleep_duration INT, deep_sleep_duration INT, rem_sleep_duration INT,
  nap_count INT, nap_duration INT,

  -- daily_spo2
  spo2_average FLOAT, breathing_disturbance_index INT,

  -- enhanced_tag
  tags TEXT,

  -- workout
  workout_count INT, workout_types TEXT,
  workout_calories INT, workout_distance INT, workout_duration INT,

  UNIQUE(user_id, date)
);
```

### weekly_summaries
```sql
CREATE TABLE weekly_summaries (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id),
  week_start     DATE NOT NULL,
  weekly_data    JSONB,
  weekly_history JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, week_start)
);
```

### fitbit_logs

Данные Fitbit Air через Google Health API. Отдельная таблица, а не расширение
`health_logs`: набор метрик другой, а шкалы скоров несравнимы, и смешивать два
определения «sleep score» в одной колонке означало бы испортить и историю Oura,
и расчёт базовых линий.

Одна строка — один день, `UNIQUE(user_id, date)` под upsert. 52 колонки:

| Группа | Колонки |
|---|---|
| Сон | `sleep_start`, `sleep_end`, `time_in_bed`, `total_sleep_duration`, `awake_time`, `light_sleep_duration`, `deep_sleep_duration`, `rem_sleep_duration`, `nap_count`, `nap_duration` |
| Вегетатика | `average_hrv`, `deep_sleep_rmssd`, `hrv_entropy`, `non_rem_hr`, `resting_hr`, `resting_hr_method`, `average_breath`, `breath_deep`, `breath_light`, `breath_rem`, `spo2_average`, `spo2_min`, `spo2_max` |
| Температура | `nightly_temp`, `baseline_temp`, `temp_rel_stddev_30d`, `temperature_deviation` |
| Активность | `steps`, `distance_m`, `total_calories`, `active_calories`, `sedentary_time`, `azm_fat_burn`, `azm_cardio`, `azm_peak`, `hr_avg`, `hr_min`, `hr_max`, `vo2_max`, `cardio_fitness_level` |
| Тренировки | `workout_count`, `workout_types`, `workout_calories`, `workout_distance`, `workout_duration` |
| Свои скоры | `readiness_score`, `sleep_score`, `activity_score` — заполняются позже |

Маркера неполной записи нет намеренно. У Oura эту роль играет
`activity_score IS NULL`, здесь вместо этого каждый прогон перезабирает последние
7 дней: Google досчитывает HRV, температуру и дыхание задним числом, и поймать
это маркером сложнее, чем просто перезаписать свежий хвост.

---

## Google Health API

Base URL: `https://health.googleapis.com/v4`

Настройка доступа — `docs/fitbit-migration/00-google-health-setup.md`,
результаты разведки по типам данных — `01-probe-results.md`.

Грабли, на которые уже наступили:

- **Скоров нет.** Ни sleep score, ни readiness, ни cardio load, ни stress
- **Статус OAuth-приложения должен быть `In production`.** В `Testing` refresh
  token живёт 7 дней, и ежедневный workflow умирает с `invalid_grant`
- **Активность фильтровать по источнику.** Без
  `users/me/dataSourceFamilies/google-wearables` в ряд попадают шаги с телефона
- **Поминутные типы только через `:dailyRollUp`.** Тело запроса — `range.start` /
  `range.end`, а не `startTime` / `endTime`; в документации формы нет, она добыта
  из discovery-документа
- **`NaN` в ответах.** `baselineTemperatureCelsius` приходит как `NaN`, пока
  не накоплена история. JSON это допускает, Supabase — нет, поэтому нечисловые
  значения пишутся как `NULL`
- **`pageSize` для `sleep` и `exercise` — максимум 25**

---

## Oura API Endpoints

Base URL: `https://api.ouraring.com/v2`

| Endpoint | Data collected |
|---|---|
| `/usercollection/daily_readiness` | readiness score + contributors |
| `/usercollection/daily_sleep` | sleep score + contributors |
| `/usercollection/daily_activity` | activity score + contributors + steps/calories |
| `/usercollection/daily_stress` | stress/recovery levels |
| `/usercollection/daily_resilience` | resilience level + contributors |
| `/usercollection/sleep` | detailed sleep metrics (HRV, HR, stages) |
| `/usercollection/daily_spo2` | SpO2 average |
| `/usercollection/enhanced_tag` | user tags |
| `/usercollection/workout` | workout count, types, calories |

Auth: `Authorization: Bearer <oura_pat>` header.

### Известные особенности API

**`daily_activity` — exclusive `end_date`**

Единственный эндпоинт с эксклюзивным `end_date`. При `start_date == end_date` возвращает 0 записей.
Все остальные эндпоинты (`daily_readiness`, `daily_sleep`, `daily_stress` и др.) используют inclusive `end_date`.

Решение: в `update_missing_dates.py` для `daily_activity` передаётся `end_date = date + 1 day`.

**`daily_stress` — единицы измерения в секундах**

`stress_high` и `recovery_high` возвращаются в **секундах**, не минутах.
В Supabase хранятся as-is (в секундах). Конвертация секунды → минуты происходит на фронте (`dashboard.js`, функция `secToMin`).

---

## Render.com — Bot Deployment

**Service:** Web Service, Python runtime
**Build command:** `pip install -r requirements.txt`
**Start command:** `python3 bot.py`
**Port:** auto-detected (Render sets `PORT` env var)

**Environment variables to set in Render dashboard:**
- `SUPABASE_URL`
- `SUPABASE_KEY` — service_role key (`sb_secret_...`)
- `TG_TOKEN`
- `OPENAI_API_KEY`
- `APP_SECRET` — случайная строка для подписи JWT дашборда (32 байта hex). Генерировать: `python3 -c "import secrets; print(secrets.token_hex(32))"`

**Auto-deploy issue:** Auto-deploy from GitHub does not always trigger. If changes don't appear after push — go to Render dashboard → Manual Deploy → Deploy latest commit.

**Register webhook after deploy or token change:**
```bash
curl "https://api.telegram.org/bot<TG_TOKEN>/setWebhook?url=https://oura-v2.onrender.com/webhook"
```
Expected response: `{"ok":true,"result":true,"description":"Webhook was set"}`

---

## GitHub Actions

Secrets required in repository settings:

| Secret | Value |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | service_role key (`sb_secret_...`) |
| `OPENAI_API_KEY` | OpenAI key |
| `TG_TOKEN` | Telegram bot token |

Workflows:

| File | Cron | Script |
|---|---|---|
| `.github/workflows/update.yml` | `0 7 * * *` | `update_missing_dates.py` |
| `.github/workflows/alert_check.yml` | `30 7 * * *` | `alert_checker.py` |
| `.github/workflows/fitbit_update.yml` | `0 9 * * *` | `fitbit_update.py` |
| `.github/workflows/send_telegram_weekly.yml` | `0 21 * * 0` | `send_telegram_message.py` |

Сбор Fitbit стоит позже сбора Oura намеренно: Google досчитывает ночные HRV,
температуру и частоту дыхания только к середине дня.

All workflows can be triggered manually via `workflow_dispatch` in the Actions tab.

---

## Dashboard — How It Works

**URL:** https://demonk03.github.io/Oura-v2/

Статичный фронтенд на GitHub Pages. Данные получает через Flask API на Render — в Supabase напрямую не ходит.

### Авторизация

```
1. Пользователь открывает login.html
2. Нажимает кнопку Telegram Login Widget
3. Telegram подтверждает личность, передаёт данные на /auth/telegram (Render)
4. bot.py проверяет подпись Telegram (HMAC-SHA256 от TG_TOKEN)
5. Ищет пользователя в Supabase по telegram_id
6. Если найден — генерирует JWT подписанный APP_SECRET (HS256, срок 7 дней)
7. JWT сохраняется в localStorage, пользователь редиректится на index.html
```

### Загрузка данных

```
1. dashboard.js читает JWT из localStorage
2. GET /api/logs?days=90  → Authorization: Bearer <jwt>
3. GET /api/weekly        → Authorization: Bearer <jwt>
4. bot.py проверяет JWT через APP_SECRET → достаёт user_id
5. Запрашивает Supabase с service_role ключом → возвращает JSON
6. dashboard.js рендерит KPI, графики, weekly recap
```

### Почему не Supabase напрямую

Supabase использует ES256 (P-256) для подписи JWT. Приватный ключ хранится у Supabase, получить его невозможно. Поэтому фронтенд не может получить токен, который Supabase примет для RLS. Решение — API proxy: бэкенд сам ходит в Supabase с service_role ключом.

### Конфигурация домена для Telegram Widget

В BotFather → Bot Settings → Domain должен быть прописан `demonk03.github.io`. Без этого виджет не отображается.

---

## Local Development

`.env` file (not committed):
```
SUPABASE_URL=...
SUPABASE_KEY=...       # sb_secret_... (service_role)
OPENAI_API_KEY=...
TG_TOKEN=...
APP_SECRET=...         # python3 -c "import secrets; print(secrets.token_hex(32))"
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_HEALTH_REFRESH_TOKEN=...   # пишется скриптом google_health_auth.py
```

Значения без кавычек. Загрузчик кавычки срежет, но при переносе в секреты
GitHub они уедут как есть и дадут `invalid_client`.

**Python.** Системный интерпретатор на маке — 3.9, а код написан под 3.11
(в Actions используется именно он). Локально нужен venv:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run data update manually:
```bash
python3 update_missing_dates.py    # Oura
python3 fitbit_update.py           # Fitbit, последние 7 дней
python3 fitbit_update.py --days 30 # другое окно
```

Run bot locally (for testing):
```bash
python3 bot.py
```
Note: webhook won't work locally without a public URL (use ngrok or test via direct Telegram API calls).

---

## Changelog / Исправленные баги

### 2026-03-29 — Activity chart пустой + Stress в секундах

**Симптом 1:** Чарт Activity не показывал данные, хотя строки в `health_logs` существовали.

**Причина:** `daily_activity` — единственный Oura API эндпоинт с exclusive `end_date`. При запросе `start_date=X, end_date=X` возвращает 0 записей. Из-за этого все поля activity (`activity_score`, `steps`, `active_calories` и др.) писались как `NULL` с самого начала заливки.

**Решение:** В `update_missing_dates.py` для `daily_activity` используется `end_date = date + 1 day`. Дополнительно `get_missing_dates` теперь также включает даты с `activity_score IS NULL` — это позволило перезалить все 56 исторических дат без ручного вмешательства.

---

**Симптом 2:** Чарт Stress показывал значения в секундах (напр. 12600 вместо 210 мин).

**Причина:** Oura API возвращает `stress_high` и `recovery_high` в секундах. Конвертации при записи в Supabase не было.

**Решение:** В `dashboard.js` добавлена функция `secToMin`, применяется везде, где отображается `stress_high`: KPI-карточка, тренд, чарт. Данные в Supabase остались в секундах — конвертация на фронте.
