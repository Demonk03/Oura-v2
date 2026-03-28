#!/usr/bin/env python3
import os
import requests
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
