# Oura-v2

Personal health tracker for Oura Ring users.

Connects to the Oura API, stores daily health data in Supabase, and delivers insights via Telegram:

- Daily alerts when key metrics (HRV, readiness, sleep score) deviate from your personal baseline
- Weekly AI-generated digest with trends and patterns

Each user self-registers via Telegram bot using their Oura Personal Access Token.

## Stack

| Layer | Service |
|---|---|
| Data source | Oura Ring API v2 |
| Database | Supabase (PostgreSQL) |
| Bot hosting | Render.com |
| Automation | GitHub Actions |
| AI analysis | OpenAI GPT |
| Delivery | Telegram Bot API |

## Architecture

```
Oura API → GitHub Actions → Supabase → alert_checker.py → Telegram
                                     → send_telegram_message.py (weekly)

Telegram → Render (bot.py) → Supabase (user registration)

Browser → login.html (Telegram Widget) → Render /auth/telegram → JWT (APP_SECRET)
Browser → dashboard.js → Render /api/logs, /api/weekly → Supabase → JSON
```

Data is collected daily via scheduled GitHub Actions workflows. Each user's Oura token is stored in Supabase — no tokens in code or environment files.

The dashboard authenticates users via Telegram Login Widget. The backend (Render/Flask) issues its own JWT signed with `APP_SECRET` and acts as a proxy to Supabase using the service_role key. The frontend never accesses Supabase directly.

## Dashboard

Available at: https://demonk03.github.io/Oura-v2/

- Login via Telegram — no password needed
- KPI cards: Readiness, Sleep, Activity, Stress with day-over-day trends
- Date selector to view any historical day
- Charts: 7 / 30 / all time range
- Weekly AI recap block

## Bot commands

```
/start                          — onboarding
/register <oura_access_token>   — connect your Oura account
/status                         — view latest metrics
/stop                           — disconnect
```

## Workflows

| Workflow | Schedule | What it does |
|---|---|---|
| Update data | Daily 07:00 UTC | Fetches Oura data for all users, writes to Supabase |
| Alert check | Daily 07:30 UTC | Checks for metric deviations, sends Telegram alerts |
| Weekly report | Sunday 21:00 UTC | Sends AI-generated weekly digest |

## Setup

See `docs/internal.md` for full setup instructions.
