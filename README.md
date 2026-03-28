# Oura-v2

Oura-v2 — personal health tracker for Oura Ring users.

Connects to the Oura API, stores daily health data in Supabase,
and delivers insights via Telegram:

- Daily alerts when key metrics (HRV, readiness, sleep score) deviate from your personal baseline
- Weekly AI-generated digest with trends and patterns

Each user self-registers via Telegram bot using their Oura Personal Access Token.

## Architecture

- **Supabase** — PostgreSQL database (users, health_logs, weekly_summaries)
- **Telegram bot** — self-registration via `/register <oura_token>`
- **GitHub Actions** — scheduled data collection and alerts

## Workflows

| Workflow | Schedule | Script |
|---|---|---|
| Update data | Daily 07:00 UTC | `update_missing_dates.py` |
| Alert check | Daily 07:30 UTC | `alert_checker.py` |
| Weekly report | Sunday 21:00 UTC | `send_telegram_message.py` |

## Setup

### 1. Supabase

Create three tables: `users`, `health_logs`, `weekly_summaries`. Schema in `docs/superpowers/specs/`.

### 2. Telegram bot

Deploy `bot.py` to Render.com (or any server). Register webhook:

```
https://api.telegram.org/bot<TG_TOKEN>/setWebhook?url=https://<your-render-url>/webhook
```

### 3. GitHub Secrets

Add to repository secrets:

- `SUPABASE_URL`
- `SUPABASE_KEY` — service_role key
- `OPENAI_API_KEY`
- `TG_TOKEN`

### 4. Environment (local)

```
SUPABASE_URL=...
SUPABASE_KEY=...
OPENAI_API_KEY=...
TG_TOKEN=...
```

## Usage

Users register via Telegram bot:

```
/register <oura_personal_access_token>
/status
/stop
```
