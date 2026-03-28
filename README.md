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
```

Data is collected daily via scheduled GitHub Actions workflows. Each user's Oura token is stored in Supabase — no tokens in code or environment files.

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
