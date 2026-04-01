#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import db
from gpt_table_analyzer import GPTTableAnalyzer

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")

WEEKLY_FIELDS = [
    "date", "readiness_score", "sleep_score", "average_heart_rate",
    "average_hrv", "total_sleep_duration", "rem_sleep_duration",
    "deep_sleep_duration", "stress_high", "recovery_high",
    "steps", "active_calories", "temperature_deviation",
]


def send_telegram(telegram_id: int, text: str) -> bool:
    response = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": telegram_id, "text": text},
        timeout=10,
    )
    return response.status_code == 200


def build_weekly_summary(user_id: str) -> None:
    """Агрегирует health_logs за последние 7 дней и пишет в weekly_summaries."""
    logs = db.get_health_logs(user_id, days=7)
    if not logs:
        return

    weekly_data = [
        {field: row.get(field) for field in WEEKLY_FIELDS}
        for row in logs
    ]

    # История — предыдущие weekly_summaries (не считая текущую неделю)
    client = db.get_client()
    history_rows = (
        client.table("weekly_summaries")
        .select("week_start, weekly_data")
        .eq("user_id", user_id)
        .order("week_start", desc=True)
        .limit(4)
        .execute()
    ).data
    weekly_history = [r["weekly_data"] for r in history_rows if r.get("weekly_data")]

    week_start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    db.upsert_weekly_summary(user_id, week_start, weekly_data, weekly_history)


def process_user(user: dict) -> None:
    user_id = user["id"]
    telegram_id = user["telegram_id"]
    print(f"[user {telegram_id}] Формируем weekly-отчёт...")

    build_weekly_summary(user_id)

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
