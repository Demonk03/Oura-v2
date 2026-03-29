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
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id  BIGINT UNIQUE NOT NULL,
  oura_pat     TEXT NOT NULL,
  timezone     TEXT NOT NULL DEFAULT 'Europe/Moscow',
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

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
| `.github/workflows/send_telegram_weekly.yml` | `0 21 * * 0` | `send_telegram_message.py` |

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
```

Run data update manually:
```bash
python3 update_missing_dates.py
```

Run bot locally (for testing):
```bash
python3 bot.py
```
Note: webhook won't work locally without a public URL (use ngrok or test via direct Telegram API calls).
