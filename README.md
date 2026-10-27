# Oura-v2

Personal health tracker. Collects daily metrics from a wearable, stores them in Supabase, and delivers insights via Telegram:

- Daily alerts when key metrics (HRV, readiness, sleep) deviate from your personal baseline
- Weekly AI-generated digest with trends and patterns
- Static dashboard on GitHub Pages

> **Migrating from Oura Ring to Fitbit Air (October 2026).**
> The Fitbit Web API shut down on 2 November 2026; its replacement is the Google Health API.
> Collection into `fitbit_logs` is live. Scoring and alerts still run on the Oura side
> until enough Fitbit history accumulates for personal baselines.
> See `plan.md` and `docs/fitbit-migration/`.

## Stack

| Layer | Service |
|---|---|
| Data sources | Oura Ring API v2, Google Health API |
| Database | Supabase (PostgreSQL) |
| Bot hosting | Render.com |
| Automation | GitHub Actions |
| AI analysis | OpenAI GPT |
| Delivery | Telegram Bot API |

## Architecture

```
Oura API          → GitHub Actions → Supabase (health_logs) → alert_checker.py → Telegram
Google Health API → GitHub Actions → Supabase (fitbit_logs)  → send_telegram_message.py (weekly)

Telegram → Render (bot.py) → Supabase (user registration)

Browser → login.html (Telegram Widget) → Render /auth/telegram → JWT (APP_SECRET)
Browser → dashboard.js → Render /api/logs, /api/weekly → Supabase → JSON
```

Data is collected daily via scheduled GitHub Actions workflows. Per-user credentials — the Oura token and the Google refresh token — live in Supabase, not in code or environment files.

The dashboard authenticates users via Telegram Login Widget. The backend (Render/Flask) issues its own JWT signed with `APP_SECRET` and acts as a proxy to Supabase using the service_role key. The frontend never accesses Supabase directly.

## Google Health API notes

Worth knowing before touching the collector:

- **No composite scores.** Sleep score, readiness, cardio load and stress are app-level metrics and are not exposed. They have to be derived from raw signals.
- **The OAuth app must be "In production".** While in "Testing", Google issues refresh tokens that expire after 7 days, which kills any scheduled job.
- **Filter activity by data source.** Without `users/me/dataSourceFamilies/google-wearables`, phone step counts are mixed into the series.
- **Minute-level data types** (`steps`, `distance`, `heart-rate`, …) must be read via `:dailyRollUp`, not `:list`.

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
| Update data | Daily 07:00 UTC | Fetches Oura data for all users |
| Update Fitbit data | Daily 09:00 UTC | Fetches Google Health data, refetches the last 7 days |
| Alert check | Daily 07:30 UTC | Checks for metric deviations, sends Telegram alerts |
| Weekly report | Sunday 21:00 UTC | Sends AI-generated weekly digest |

Fitbit collection runs later in the day on purpose: Google backfills overnight HRV, temperature and respiratory rate only by midday.

## Setup

See `docs/internal.md` for the Oura side and `docs/fitbit-migration/00-google-health-setup.md` for Google Health.

## Privacy

[Privacy policy](https://demonk03.github.io/Oura-v2/privacy.html)
