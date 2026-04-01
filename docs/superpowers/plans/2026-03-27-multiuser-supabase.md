# Oura-v2: Мультипользовательская архитектура (Supabase) — Implementation Plan

**СТАТУС: ВЫПОЛНЕНО 2026-03-29**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать новый проект Oura-v2 с поддержкой до 5 пользователей — Supabase как БД, Telegram-бот для регистрации, GitHub Actions для сбора данных и уведомлений.

**Architecture:** Supabase хранит пользователей и все данные здоровья. Telegram-бот (Flask webhook на Render.com) принимает регистрацию. GitHub Actions итерируется по активным пользователям, собирает данные через Oura API и пишет в Supabase. Логика алертов и GPT-анализа не меняется — меняется только источник/получатель данных.

**Tech Stack:** Python 3.11, supabase-py, Flask, python-telegram-bot, pandas, requests, GitHub Actions, Supabase (PostgreSQL), Render.com

**Design doc:** `docs/superpowers/specs/2026-03-27-multiuser-supabase-design.md`

---

## Task 1: Инициализация проекта Oura-v2

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1:** Инициализировать git-репозиторий в папке `Oura-v2/`
  ```bash
  cd "/Users/dkossenkov/Documents/Private files/AI/Oura-v2"
  git init
  ```

- [ ] **Step 2:** Создать `.gitignore`
  ```
  .env
  __pycache__/
  *.pyc
  .DS_Store
  ```

- [ ] **Step 3:** Создать `requirements.txt`
  ```
  requests==2.31.0
  pandas==2.1.4
  python-dotenv==1.0.0
  supabase==2.4.0
  Flask==3.0.2
  python-telegram-bot==21.0.1
  ```

- [ ] **Step 4:** Создать `.env.example`
  ```
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_KEY=service_role_key_here
  OPENAI_API_KEY=sk-...
  TG_TOKEN=bot_token_here
  WEBHOOK_URL=https://your-app.onrender.com
  ```

- [ ] **Step 5:** Commit
  ```bash
  git add .
  git commit -m "init: project structure"
  ```

---

## Task 2: Настройка Supabase (ручной шаг)

**Это ручной шаг — выполняется в браузере, не кодом.**

- [ ] **Step 1:** Зайти на [supabase.com](https://supabase.com), создать новый проект `oura-v2`

- [ ] **Step 2:** В SQL Editor выполнить — создать таблицу `users`:
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

- [ ] **Step 3:** Создать таблицу `health_logs`:
  ```sql
  CREATE TABLE health_logs (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    date    DATE NOT NULL,
    readiness_score INT, readiness_activity_balance_score INT,
    readiness_body_temp_score INT, readiness_hrv_balance_score INT,
    readiness_prev_day_score INT, readiness_prev_night_score INT,
    readiness_recovery_score INT, readiness_resting_hr_score INT,
    readiness_sleep_balance_score INT,
    temperature_deviation FLOAT, temperature_trend_deviation FLOAT,
    sleep_score INT, sleep_deep_score INT, sleep_efficiency_score INT,
    sleep_latency_score INT, sleep_rem_score INT,
    sleep_restfulness_score INT, sleep_timing_score INT, sleep_total_score INT,
    activity_score INT, activity_meet_targets_score INT,
    activity_move_hour_score INT, activity_recovery_score INT,
    activity_stay_active_score INT, activity_train_freq_score INT,
    activity_train_vol_score INT,
    steps INT, active_calories INT, total_calories INT,
    walking_distance INT, high_activity_time INT, sedentary_time INT,
    resilience_level TEXT, resilience_sleep_score INT,
    resilience_daytime_score INT, resilience_stress_score INT,
    stress_high INT, recovery_high INT, day_summary TEXT,
    average_heart_rate FLOAT, lowest_heart_rate INT,
    average_hrv FLOAT, average_breath FLOAT,
    efficiency INT, latency INT, time_in_bed INT,
    total_sleep_duration INT, awake_time INT,
    light_sleep_duration INT, deep_sleep_duration INT,
    rem_sleep_duration INT, nap_count INT, nap_duration INT,
    spo2_average FLOAT, breathing_disturbance_index INT,
    tags TEXT,
    workout_count INT, workout_types TEXT,
    workout_calories INT, workout_distance INT, workout_duration INT,
    UNIQUE(user_id, date)
  );
  ```

- [ ] **Step 4:** Создать таблицу `weekly_summaries`:
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

- [ ] **Step 5:** Скопировать `Project URL` и `service_role` key из Settings → API → вставить в `.env`

---

## Task 3: db.py — модуль работы с Supabase

**Files:**
- Create: `db.py`

- [ ] **Step 1:** Создать `db.py` с полным набором функций:
  ```python
  import os
  import json
  from datetime import datetime, timedelta
  from dotenv import load_dotenv
  from supabase import create_client, Client

  load_dotenv()

  def get_client() -> Client:
      url = os.getenv("SUPABASE_URL")
      key = os.getenv("SUPABASE_KEY")
      if not url or not key:
          raise ValueError("SUPABASE_URL и SUPABASE_KEY должны быть в .env")
      return create_client(url, key)

  def get_active_users() -> list[dict]:
      """Возвращает список активных пользователей."""
      client = get_client()
      response = client.table("users").select("*").eq("is_active", True).execute()
      return response.data

  def get_user_by_telegram_id(telegram_id: int) -> dict | None:
      client = get_client()
      response = client.table("users").select("*").eq("telegram_id", telegram_id).execute()
      return response.data[0] if response.data else None

  def insert_user(telegram_id: int, oura_pat: str, timezone: str = "Europe/Moscow") -> dict:
      client = get_client()
      response = client.table("users").insert({
          "telegram_id": telegram_id,
          "oura_pat": oura_pat,
          "timezone": timezone,
      }).execute()
      return response.data[0]

  def deactivate_user(telegram_id: int) -> None:
      client = get_client()
      client.table("users").update({"is_active": False}).eq("telegram_id", telegram_id).execute()

  def upsert_health_log(user_id: str, date: str, fields: dict) -> None:
      """Вставляет или обновляет запись health_logs для user_id + date."""
      client = get_client()
      data = {"user_id": user_id, "date": date, **fields}
      client.table("health_logs").upsert(data, on_conflict="user_id,date").execute()

  def get_health_logs(user_id: str, days: int = 30) -> list[dict]:
      """Возвращает записи health_logs за последние N дней для пользователя."""
      start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
      client = get_client()
      response = (
          client.table("health_logs")
          .select("*")
          .eq("user_id", user_id)
          .gte("date", start_date)
          .order("date")
          .execute()
      )
      return response.data

  def get_latest_health_log(user_id: str) -> dict | None:
      client = get_client()
      response = (
          client.table("health_logs")
          .select("*")
          .eq("user_id", user_id)
          .order("date", desc=True)
          .limit(1)
          .execute()
      )
      return response.data[0] if response.data else None

  def get_weekly_summary(user_id: str) -> dict | None:
      client = get_client()
      response = (
          client.table("weekly_summaries")
          .select("*")
          .eq("user_id", user_id)
          .order("week_start", desc=True)
          .limit(1)
          .execute()
      )
      return response.data[0] if response.data else None

  def upsert_weekly_summary(user_id: str, week_start: str, weekly_data: dict, weekly_history: list) -> None:
      client = get_client()
      client.table("weekly_summaries").upsert({
          "user_id": user_id,
          "week_start": week_start,
          "weekly_data": weekly_data,
          "weekly_history": weekly_history,
      }, on_conflict="user_id,week_start").execute()
  ```

- [ ] **Step 2:** Проверить подключение локально:
  ```bash
  python3 -c "import db; print(db.get_active_users())"
  ```
  Ожидаемый вывод: `[]` (таблица пустая)

- [ ] **Step 3:** Commit
  ```bash
  git add db.py
  git commit -m "feat: add db.py — Supabase CRUD module"
  ```

---

## Task 4: update_missing_dates.py — сбор данных для всех пользователей

**Files:**
- Create: `update_missing_dates.py`

За основу берём логику из `Oura/update_missing_dates.py`, переписываем источник/получатель данных.

- [ ] **Step 1:** Создать `update_missing_dates.py`:
  ```python
  #!/usr/bin/env python3
  import os
  import requests
  import json
  from datetime import datetime, timedelta
  from dotenv import load_dotenv
  import db

  load_dotenv()

  BASE_URL = "https://api.ouraring.com/v2"
  START_DATE = "2026-02-01"

  ENDPOINTS = {
      "daily_readiness": "/usercollection/daily_readiness",
      "daily_sleep": "/usercollection/daily_sleep",
      "daily_activity": "/usercollection/daily_activity",
      "daily_stress": "/usercollection/daily_stress",
      "daily_resilience": "/usercollection/daily_resilience",
      "sleep": "/usercollection/sleep",
      "daily_spo2": "/usercollection/daily_spo2",
      "enhanced_tag": "/usercollection/enhanced_tag",
      "workout": "/usercollection/workout",
  }

  def fetch_endpoint(oura_pat: str, endpoint: str, start_date: str, end_date: str) -> list:
      headers = {"Authorization": f"Bearer {oura_pat}"}
      params = {"start_date": start_date, "end_date": end_date}
      response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=30)
      response.raise_for_status()
      return response.json().get("data", [])

  def build_day_fields(date: str, oura_pat: str) -> dict:
      """Собирает все поля для одного дня из всех эндпоинтов."""
      fields = {}

      # daily_readiness
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_readiness"], date, date)
      if data:
          r = data[0]
          fields.update({
              "readiness_score": r.get("score"),
              "temperature_deviation": r.get("temperature_deviation"),
              "temperature_trend_deviation": r.get("temperature_trend_deviation"),
          })
          for k, v in (r.get("contributors") or {}).items():
              fields[f"readiness_{k}_score"] = v

      # daily_sleep
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_sleep"], date, date)
      if data:
          r = data[0]
          fields["sleep_score"] = r.get("score")
          for k, v in (r.get("contributors") or {}).items():
              fields[f"sleep_{k}_score"] = v

      # daily_activity
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_activity"], date, date)
      if data:
          r = data[0]
          fields.update({
              "activity_score": r.get("score"),
              "steps": r.get("steps"),
              "active_calories": r.get("active_calories"),
              "total_calories": r.get("total_calories"),
              "walking_distance": r.get("equivalent_walking_distance"),
              "high_activity_time": r.get("high_activity_time"),
              "sedentary_time": r.get("sedentary_time"),
          })
          for k, v in (r.get("contributors") or {}).items():
              fields[f"activity_{k}_score"] = v

      # daily_stress
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_stress"], date, date)
      if data:
          r = data[0]
          fields.update({
              "stress_high": r.get("stress_high"),
              "recovery_high": r.get("recovery_high"),
              "day_summary": r.get("day_summary"),
          })

      # daily_resilience
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_resilience"], date, date)
      if data:
          r = data[0]
          fields["resilience_level"] = r.get("level")
          for k, v in (r.get("contributors") or {}).items():
              fields[f"resilience_{k}_score"] = v

      # sleep (детальные данные — long_sleep)
      data = fetch_endpoint(oura_pat, ENDPOINTS["sleep"], date, date)
      long_sleeps = [s for s in data if s.get("type") == "long_sleep"]
      short_sleeps = [s for s in data if s.get("type") == "short_sleep"]
      if long_sleeps:
          s = long_sleeps[0]
          fields.update({
              "average_heart_rate": s.get("average_heart_rate"),
              "lowest_heart_rate": s.get("lowest_heart_rate"),
              "average_hrv": s.get("average_hrv"),
              "average_breath": s.get("average_breath"),
              "efficiency": s.get("efficiency"),
              "latency": s.get("latency"),
              "time_in_bed": s.get("time_in_bed"),
              "total_sleep_duration": s.get("total_sleep_duration"),
              "awake_time": s.get("awake_time"),
              "light_sleep_duration": s.get("light_sleep_duration"),
              "deep_sleep_duration": s.get("deep_sleep_duration"),
              "rem_sleep_duration": s.get("rem_sleep_duration"),
          })
      if short_sleeps:
          fields["nap_count"] = len(short_sleeps)
          fields["nap_duration"] = sum(s.get("total_sleep_duration", 0) or 0 for s in short_sleeps)

      # daily_spo2
      data = fetch_endpoint(oura_pat, ENDPOINTS["daily_spo2"], date, date)
      if data:
          r = data[0]
          fields["spo2_average"] = (r.get("spo2_percentage") or {}).get("average")
          fields["breathing_disturbance_index"] = r.get("breathing_disturbance_index")

      # enhanced_tag
      data = fetch_endpoint(oura_pat, ENDPOINTS["enhanced_tag"], date, date)
      if data:
          fields["tags"] = "|".join(t.get("tag_type_code", "") for t in data)

      # workout
      data = fetch_endpoint(oura_pat, ENDPOINTS["workout"], date, date)
      if data:
          fields["workout_count"] = len(data)
          fields["workout_types"] = "|".join(w.get("activity", "") for w in data)
          fields["workout_calories"] = sum(w.get("calories", 0) or 0 for w in data)
          fields["workout_distance"] = sum(w.get("distance", 0) or 0 for w in data)
          fields["workout_duration"] = sum(w.get("duration", 0) or 0 for w in data)

      return fields

  def get_missing_dates(user_id: str) -> list[str]:
      """Возвращает даты от START_DATE до вчера, которых нет в health_logs."""
      logs = db.get_health_logs(user_id, days=365)
      existing = {r["date"] for r in logs}
      yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
      all_dates = []
      current = datetime.strptime(START_DATE, "%Y-%m-%d")
      end = datetime.strptime(yesterday, "%Y-%m-%d")
      while current <= end:
          d = current.strftime("%Y-%m-%d")
          if d not in existing:
              all_dates.append(d)
          current += timedelta(days=1)
      return all_dates

  def update_user(user: dict) -> None:
      user_id = user["id"]
      oura_pat = user["oura_pat"]
      telegram_id = user["telegram_id"]
      print(f"[user {telegram_id}] Проверяем пропущенные даты...")
      missing = get_missing_dates(user_id)
      if not missing:
          print(f"[user {telegram_id}] Нет пропущенных дат.")
          return
      print(f"[user {telegram_id}] Дозаписываем {len(missing)} дат...")
      for date in missing:
          try:
              fields = build_day_fields(date, oura_pat)
              db.upsert_health_log(user_id, date, fields)
              print(f"[user {telegram_id}] {date} — записано")
          except Exception as e:
              print(f"[user {telegram_id}] {date} — ошибка: {e}")

  def main():
      users = db.get_active_users()
      print(f"Активных пользователей: {len(users)}")
      for user in users:
          update_user(user)

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2:** Добавить тестового пользователя в Supabase вручную (через SQL Editor) для локального теста:
  ```sql
  INSERT INTO users (telegram_id, oura_pat) VALUES (123456789, 'ВАШ_РЕАЛЬНЫЙ_OURA_PAT');
  ```

- [ ] **Step 3:** Запустить локально и проверить что данные появляются в Supabase:
  ```bash
  python3 update_missing_dates.py
  ```
  Ожидаемый вывод: `[user 123456789] 2026-02-01 — записано` ... и т.д.

- [ ] **Step 4:** Проверить в Supabase Dashboard → Table Editor → `health_logs` — должны появиться строки

- [ ] **Step 5:** Commit
  ```bash
  git add update_missing_dates.py
  git commit -m "feat: add update_missing_dates.py — multi-user Supabase"
  ```

---

## Task 5: alert_checker.py — алерты для всех пользователей

**Files:**
- Create: `alert_checker.py`

Логика паттернов не меняется. Меняется источник данных (Supabase вместо CSV) и получатель (telegram_id каждого пользователя).

- [ ] **Step 1:** Создать `alert_checker.py`:
  ```python
  #!/usr/bin/env python3
  import os
  import json
  import pandas as pd
  import requests
  from dotenv import load_dotenv
  import db

  load_dotenv()

  OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
  TG_TOKEN = os.getenv("TG_TOKEN")
  BASELINE_DAYS = 30

  def get_baseline(df: pd.DataFrame, metric: str) -> float | None:
      window = df.tail(BASELINE_DAYS)[metric].dropna()
      return float(window.median()) if len(window) > 0 else None

  def check_alerts(df: pd.DataFrame) -> list[dict]:
      triggered = []
      today = df.tail(1).iloc[0]

      readiness = today.get("readiness_score")
      if pd.notna(readiness) and readiness < 70:
          triggered.append({"rule": "readiness_low", "description": f"Готовность {int(readiness)} — ниже порога 70"})

      sleep = today.get("sleep_score")
      if pd.notna(sleep) and sleep < 60:
          triggered.append({"rule": "sleep_crash", "description": f"Sleep score {int(sleep)} — критически низкий"})

      temp = today.get("temperature_deviation")
      if pd.notna(temp) and abs(temp) > 0.3:
          triggered.append({"rule": "temperature_spike", "description": f"Отклонение температуры {temp:+.2f}°C — возможный маркер болезни"})

      baseline_sleep = get_baseline(df, "sleep_score")
      if baseline_sleep:
          last_5 = df.tail(5)["sleep_score"].dropna()
          if len(last_5) == 5 and all(v < baseline_sleep for v in last_5):
              triggered.append({"rule": "sleep_trend_down", "description": f"Sleep score ниже нормы ({int(baseline_sleep)}) 5 дней подряд"})

      baseline_duration = get_baseline(df, "total_sleep_duration")
      if baseline_duration:
          last_5 = df.tail(5)["total_sleep_duration"].dropna()
          if len(last_5) == 5 and all(v < baseline_duration for v in last_5):
              triggered.append({"rule": "sleep_duration_trend", "description": f"Продолжительность сна ниже нормы ({int(baseline_duration)} мин) 5 дней подряд"})

      baseline_rem = get_baseline(df, "rem_sleep_duration")
      if baseline_rem:
          last_5 = df.tail(5)["rem_sleep_duration"].dropna()
          if len(last_5) == 5 and all(v < baseline_rem for v in last_5):
              triggered.append({"rule": "rem_trend_down", "description": f"REM-сон ниже нормы ({int(baseline_rem)} мин) 5 дней подряд"})

      baseline_hr = get_baseline(df, "average_heart_rate")
      if baseline_hr:
          last_3 = df.tail(3)["average_heart_rate"].dropna()
          if len(last_3) == 3 and all(v > baseline_hr + 3 for v in last_3):
              triggered.append({"rule": "hr_elevated", "description": f"Ночной пульс выше нормы ({baseline_hr:.1f}) на 3+ уд/мин 3 ночи подряд"})

      last_14 = df.tail(14)
      prev_14 = df.tail(28).head(14)
      if len(last_14) == 14 and len(prev_14) == 14:
          balance_now = float((last_14["stress_high"].fillna(0) - last_14["recovery_high"].fillna(0)).mean())
          balance_prev = float((prev_14["stress_high"].fillna(0) - prev_14["recovery_high"].fillna(0)).mean())
          if balance_prev != 0 and (balance_now - balance_prev) / abs(balance_prev) > 0.15:
              triggered.append({"rule": "stress_balance_worsening", "description": f"Баланс стресс/восстановление ухудшился: {balance_prev:.0f} → {balance_now:.0f} мин/день"})

      baseline_hrv = get_baseline(df, "average_hrv")
      if baseline_hrv and len(last_14) == 14:
          hrv_14_avg = last_14["average_hrv"].dropna().mean()
          if pd.notna(hrv_14_avg) and hrv_14_avg < baseline_hrv * 0.9:
              triggered.append({"rule": "hrv_trend_down", "description": f"HRV {hrv_14_avg:.1f} мс — на 10%+ ниже нормы ({baseline_hrv:.1f} мс) за 14 дней"})

      return triggered

  def build_gpt_prompt(triggered_alerts: list, df: pd.DataFrame, baseline: dict) -> str:
      alerts_text = "\n".join(f"- {a['description']}" for a in triggered_alerts)
      recent = df[["date", "readiness_score", "sleep_score", "average_heart_rate",
                   "average_hrv", "total_sleep_duration", "rem_sleep_duration",
                   "stress_high", "recovery_high", "temperature_deviation"]].tail(7).copy()
      recent["date"] = recent["date"].astype(str)
      recent_json = recent.to_json(orient="records", indent=2, force_ascii=False)
      return f"""Ты — персональный health-аналитик. Пользователь носит кольцо Oura.

  Сработали следующие паттерны:
  {alerts_text}

  Данные за последние 7 дней:
  {recent_json}

  Личная базовая линия (медиана за 30 дней):
  {json.dumps(baseline, ensure_ascii=False, indent=2)}

  Напиши короткое сообщение для Telegram (3-5 предложений):
  - Скажи что именно произошло и насколько это отклонение от нормы
  - Если сработало несколько алертов — объедини в связный текст
  - Добавь 1 практическую рекомендацию
  - Тон: спокойный, без паники, по делу
  - Без эмодзи, без markdown-разметки"""

  def call_gpt(prompt: str) -> str:
      response = requests.post(
          "https://api.openai.com/v1/chat/completions",
          headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
          json={"model": "gpt-4", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500, "temperature": 0.7},
          timeout=30,
      )
      response.raise_for_status()
      return response.json()["choices"][0]["message"]["content"]

  def send_telegram(telegram_id: int, text: str) -> bool:
      response = requests.post(
          f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
          data={"chat_id": telegram_id, "text": text},
          timeout=10,
      )
      return response.status_code == 200

  def process_user(user: dict) -> None:
      user_id = user["id"]
      telegram_id = user["telegram_id"]
      print(f"[user {telegram_id}] Проверяем алерты...")

      logs = db.get_health_logs(user_id, days=35)
      if not logs:
          print(f"[user {telegram_id}] Нет данных.")
          return

      df = pd.DataFrame(logs)
      df["date"] = pd.to_datetime(df["date"])
      df = df.sort_values("date").reset_index(drop=True)
      for col in df.columns:
          if col not in ("date", "user_id", "id", "resilience_level", "day_summary", "tags", "workout_types"):
              df[col] = pd.to_numeric(df[col], errors="coerce")

      triggered = check_alerts(df)
      if not triggered:
          print(f"[user {telegram_id}] Алертов нет.")
          return

      print(f"[user {telegram_id}] Сработало алертов: {len(triggered)}")
      baseline = {m: get_baseline(df, m) for m in ["readiness_score", "sleep_score", "average_heart_rate",
                   "average_hrv", "total_sleep_duration", "stress_high", "recovery_high", "rem_sleep_duration"]}
      prompt = build_gpt_prompt(triggered, df, baseline)
      message = call_gpt(prompt)
      sent = send_telegram(telegram_id, message)
      print(f"[user {telegram_id}] {'Отправлено.' if sent else 'Ошибка отправки.'}")

  def main():
      users = db.get_active_users()
      print(f"Активных пользователей: {len(users)}")
      for user in users:
          process_user(user)

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2:** Проверить локально (нужен OPENAI_API_KEY + данные в Supabase из Task 4):
  ```bash
  python3 alert_checker.py
  ```
  Ожидаемый вывод: `[user 123456789] Алертов нет.` или сообщение об алерте

- [ ] **Step 3:** Commit
  ```bash
  git add alert_checker.py
  git commit -m "feat: add alert_checker.py — multi-user Supabase"
  ```

---

## Task 6: gpt_table_analyzer.py и send_telegram_message.py — weekly-отчёт

**Files:**
- Create: `gpt_table_analyzer.py`
- Create: `send_telegram_message.py`

- [ ] **Step 1:** Скопировать `gpt_table_analyzer.py` из `Oura/` — логика промпта не меняется, только убираем работу с файлами:
  ```bash
  cp "../Oura/gpt_table_analyzer.py" .
  ```

- [ ] **Step 2:** Создать `send_telegram_message.py` для multi-user weekly:
  ```python
  #!/usr/bin/env python3
  import os
  import json
  import requests
  from datetime import datetime, timedelta
  from dotenv import load_dotenv
  import db
  from gpt_table_analyzer import GPTTableAnalyzer

  load_dotenv()

  TG_TOKEN = os.getenv("TG_TOKEN")

  def send_telegram(telegram_id: int, text: str) -> bool:
      response = requests.post(
          f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
          data={"chat_id": telegram_id, "text": text},
          timeout=10,
      )
      return response.status_code == 200

  def process_user(user: dict) -> None:
      user_id = user["id"]
      telegram_id = user["telegram_id"]
      print(f"[user {telegram_id}] Формируем weekly-отчёт...")

      summary = db.get_weekly_summary(user_id)
      if not summary:
          print(f"[user {telegram_id}] Нет weekly_summary.")
          return

      analyzer = GPTTableAnalyzer()
      weekly_data = summary.get("weekly_data", {})
      weekly_history = summary.get("weekly_history", [])
      formatted = analyzer.format_weekly_data_for_gpt(weekly_data)
      gpt_response = analyzer.send_weekly_data_to_gpt(formatted, weekly_history)

      if "choices" in gpt_response:
          text = gpt_response["choices"][0]["message"]["content"]
          sent = send_telegram(telegram_id, text)
          print(f"[user {telegram_id}] {'Отправлено.' if sent else 'Ошибка.'}")
      else:
          print(f"[user {telegram_id}] Ошибка GPT.")

  def main():
      users = db.get_active_users()
      for user in users:
          process_user(user)

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 3:** Commit
  ```bash
  git add gpt_table_analyzer.py send_telegram_message.py
  git commit -m "feat: add weekly GPT report — multi-user Supabase"
  ```

---

## Task 7: bot.py — Telegram-бот регистрации

**Files:**
- Create: `bot.py`

- [ ] **Step 1:** Создать `bot.py` (Flask webhook + python-telegram-bot):
  ```python
  #!/usr/bin/env python3
  import os
  import requests
  from flask import Flask, request
  from dotenv import load_dotenv
  import db

  load_dotenv()

  TG_TOKEN = os.getenv("TG_TOKEN")
  OURA_BASE_URL = "https://api.ouraring.com/v2"

  app = Flask(__name__)

  def send_message(chat_id: int, text: str) -> None:
      requests.post(
          f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
          data={"chat_id": chat_id, "text": text},
          timeout=10,
      )

  def validate_oura_token(oura_pat: str) -> bool:
      """Делает тестовый запрос к Oura API чтобы проверить токен."""
      try:
          response = requests.get(
              f"{OURA_BASE_URL}/usercollection/personal_info",
              headers={"Authorization": f"Bearer {oura_pat}"},
              timeout=10,
          )
          return response.status_code == 200
      except Exception:
          return False

  def handle_register(chat_id: int, oura_pat: str) -> None:
      existing = db.get_user_by_telegram_id(chat_id)
      if existing and existing["is_active"]:
          send_message(chat_id, "Ты уже зарегистрирован. Используй /stop чтобы отключиться.")
          return

      send_message(chat_id, "Проверяю токен Oura...")
      if not validate_oura_token(oura_pat):
          send_message(chat_id, "Токен не работает. Проверь его в приложении Oura: Profile → Personal Access Token.")
          return

      if existing and not existing["is_active"]:
          # реактивация
          db.get_client().table("users").update({"oura_pat": oura_pat, "is_active": True}).eq("telegram_id", chat_id).execute()
      else:
          db.insert_user(telegram_id=chat_id, oura_pat=oura_pat)

      send_message(chat_id, "Готово! Данные начнут собираться завтра утром. Еженедельный отчёт — по воскресеньям.")

  def handle_status(chat_id: int) -> None:
      user = db.get_user_by_telegram_id(chat_id)
      if not user or not user["is_active"]:
          send_message(chat_id, "Ты не зарегистрирован. Используй /register <oura_token>.")
          return

      log = db.get_latest_health_log(user["id"])
      if not log:
          send_message(chat_id, "Данных пока нет. Подожди до завтра после 10:00 МСК.")
          return

      send_message(chat_id, (
          f"Последние данные ({log['date']}):\n"
          f"Готовность: {log.get('readiness_score', '—')}\n"
          f"Сон: {log.get('sleep_score', '—')}\n"
          f"HRV: {log.get('average_hrv', '—')} мс\n"
          f"Пульс: {log.get('average_heart_rate', '—')} уд/мин"
      ))

  def handle_stop(chat_id: int) -> None:
      user = db.get_user_by_telegram_id(chat_id)
      if not user:
          send_message(chat_id, "Ты не зарегистрирован.")
          return
      db.deactivate_user(chat_id)
      send_message(chat_id, "Отключено. Данные больше не собираются. /register чтобы включить снова.")

  @app.route(f"/{TG_TOKEN}", methods=["POST"])
  def webhook():
      update = request.get_json()
      message = update.get("message", {})
      chat_id = message.get("chat", {}).get("id")
      text = message.get("text", "").strip()

      if not chat_id or not text:
          return "ok"

      if text.startswith("/register"):
          parts = text.split(maxsplit=1)
          if len(parts) < 2:
              send_message(chat_id, "Использование: /register <oura_token>")
          else:
              handle_register(chat_id, parts[1].strip())

      elif text == "/status":
          handle_status(chat_id)

      elif text == "/stop":
          handle_stop(chat_id)

      else:
          send_message(chat_id, "Команды: /register <oura_token> | /status | /stop")

      return "ok"

  @app.route("/health")
  def health():
      return "ok"

  if __name__ == "__main__":
      app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
  ```

- [ ] **Step 2:** Протестировать локально через ngrok (опционально) или пропустить до деплоя на Render

- [ ] **Step 3:** Commit
  ```bash
  git add bot.py
  git commit -m "feat: add bot.py — Telegram registration webhook"
  ```

---

## Task 8: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/update.yml`
- Create: `.github/workflows/alert_check.yml`
- Create: `.github/workflows/send_telegram_weekly.yml`

- [ ] **Step 1:** Создать `.github/workflows/update.yml`:
  ```yaml
  name: Update Oura Data (v2)

  on:
    schedule:
      - cron: "0 7 * * *"
    workflow_dispatch:

  jobs:
    update-data:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -r requirements.txt
        - name: Run update
          env:
            SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
            SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          run: python update_missing_dates.py
  ```

- [ ] **Step 2:** Создать `.github/workflows/alert_check.yml`:
  ```yaml
  name: Oura Alert Check (v2)

  on:
    schedule:
      - cron: "30 7 * * *"
    workflow_dispatch:

  jobs:
    check-alerts:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -r requirements.txt
        - name: Run alert checker
          env:
            SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
            SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
            OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
            TG_TOKEN: ${{ secrets.TG_TOKEN }}
          run: python alert_checker.py
  ```

- [ ] **Step 3:** Создать `.github/workflows/send_telegram_weekly.yml`:
  ```yaml
  name: Send Oura Weekly (v2)

  on:
    schedule:
      - cron: "0 21 * * 0"
    workflow_dispatch:

  jobs:
    send-weekly:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -r requirements.txt
        - name: Run weekly report
          env:
            SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
            SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
            OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
            TG_TOKEN: ${{ secrets.TG_TOKEN }}
          run: python send_telegram_message.py
  ```

- [ ] **Step 4:** Commit
  ```bash
  git add .github/
  git commit -m "feat: add GitHub Actions workflows — multi-user"
  ```

---

## Task 9: GitHub — создать репозиторий и добавить секреты (ручной шаг)

- [ ] **Step 1:** Создать приватный репозиторий `oura-v2` на GitHub

- [ ] **Step 2:** Привязать локальный репозиторий:
  ```bash
  git remote add origin https://github.com/ВАШ_USERNAME/oura-v2.git
  git push -u origin main
  ```

- [ ] **Step 3:** В Settings → Secrets → Actions добавить:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `OPENAI_API_KEY`
  - `TG_TOKEN`

- [ ] **Step 4:** Запустить `update.yml` вручную через Actions → workflow_dispatch → убедиться что данные появились в Supabase

---

## Task 10: Деплой bot.py на Render.com (ручной шаг)

- [ ] **Step 1:** Зайти на [render.com](https://render.com), создать аккаунт

- [ ] **Step 2:** New → Web Service → подключить GitHub репозиторий `oura-v2`

- [ ] **Step 3:** Настройки:
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `python bot.py`
  - Environment Variables: `TG_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`

- [ ] **Step 4:** После деплоя скопировать URL вида `https://oura-v2.onrender.com`

- [ ] **Step 5:** Зарегистрировать webhook в Telegram:
  ```bash
  curl "https://api.telegram.org/bot<TG_TOKEN>/setWebhook?url=https://oura-v2.onrender.com/<TG_TOKEN>"
  ```
  Ожидаемый ответ: `{"ok":true,"result":true}`

---

## Task 11: End-to-end тест

- [ ] **Step 1:** Написать боту `/register <ВАШ_OURA_PAT>` → получить подтверждение

- [ ] **Step 2:** Проверить в Supabase Dashboard → `users` — появилась запись

- [ ] **Step 3:** Написать `/status` → получить последние данные (или "данных пока нет" если update ещё не запускался)

- [ ] **Step 4:** Запустить `update.yml` вручную → проверить `health_logs` в Supabase

- [ ] **Step 5:** Написать `/status` повторно → должны появиться актуальные данные

- [ ] **Step 6:** Написать `/stop` → проверить `is_active = false` в Supabase

---

## Итог

После выполнения всех задач:
- Пользователи регистрируются сами через Telegram-бота
- Данные каждого пользователя изолированы в Supabase по `user_id`
- GitHub Actions ежедневно обновляет данные для всех активных пользователей
- Алерты и weekly-отчёты уходят каждому в его Telegram
- Добавить нового пользователя = он сам пишет боту `/register`
