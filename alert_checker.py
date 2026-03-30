#!/usr/bin/env python3
import os
import json
import pandas as pd
import requests
from dotenv import load_dotenv
import db

load_dotenv()

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
TG_TOKEN = (os.getenv("TG_TOKEN") or "").strip()
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
        balance_now = float((last_14["stress_high"].fillna(0) - last_14["recovery_high"].fillna(0)).mean()) / 60
        balance_prev = float((prev_14["stress_high"].fillna(0) - prev_14["recovery_high"].fillna(0)).mean()) / 60
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
    recent["stress_high"] = (recent["stress_high"] / 60).round(0)
    recent["recovery_high"] = (recent["recovery_high"] / 60).round(0)
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
        try:
            process_user(user)
        except Exception as e:
            print(f"[user {user.get('telegram_id')}] Ошибка: {e}")


if __name__ == "__main__":
    main()
