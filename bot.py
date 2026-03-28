#!/usr/bin/env python3
import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
import db

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
OURA_BASE_URL = "https://api.ouraring.com/v2"

OURA_TOKEN_KEYBOARD = {
    "inline_keyboard": [[
        {"text": "Получить токен →", "url": "https://cloud.ouraring.com/personal-access-tokens"}
    ]]
}

app = Flask(__name__)


def send_message(chat_id: int, text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def send_message_with_keyboard(chat_id: int, text: str, keyboard: dict) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "reply_markup": keyboard},
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
        send_message(chat_id, (
            "Не получилось подключиться — токен не работает.\n\n"
            "Проверь его на странице: https://cloud.ouraring.com/personal-access-tokens\n"
            "Убедись, что скопировал токен полностью, без лишних пробелов."
        ))
        return

    if existing and not existing["is_active"]:
        # реактивация
        db.get_client().table("users").update({"oura_pat": oura_pat, "is_active": True}).eq("telegram_id", chat_id).execute()
    else:
        db.insert_user(telegram_id=chat_id, oura_pat=oura_pat)

    send_message(chat_id, (
        "Отлично, всё готово! Я уже начал собирать твои данные.\n\n"
        "Буду присылать алёрты, если замечу что-то необычное, "
        "и каждое воскресенье — дайджест твоей недели.\n\n"
        "/status — посмотреть последние показатели\n"
        "/stop — отключиться"
    ))


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


def handle_start(chat_id: int) -> None:
    user = db.get_user_by_telegram_id(chat_id)
    if user and user["is_active"]:
        send_message(chat_id, (
            "Привет! Я уже собираю и анализирую твои данные.\n\n"
            "/status — последние показатели\n"
            "/stop — отключиться"
        ))
    else:
        send_message_with_keyboard(chat_id, (
            "Привет! Я Oura Helper — помогаю следить за показателями кольца Oura.\n\n"
            "Анализирую твои данные, присылаю алёрты при отклонениях "
            "от личной нормы и еженедельный дайджест по воскресеньям.\n\n"
            "Для подключения нужен Personal Access Token.\n\n"
            "Когда получишь — отправь: /register <токен>"
        ), OURA_TOKEN_KEYBOARD)


def handle_stop(chat_id: int) -> None:
    user = db.get_user_by_telegram_id(chat_id)
    if not user:
        send_message(chat_id, "Ты не зарегистрирован.")
        return
    db.deactivate_user(chat_id)
    send_message(chat_id, "Отключено. Данные больше не собираются. /register чтобы включить снова.")


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return "ok"

    if text == "/start":
        handle_start(chat_id)

    elif text.startswith("/register"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Использование: /register <oura_token>\n\nПолучить токен: https://cloud.ouraring.com/personal-access-tokens")
        else:
            handle_register(chat_id, parts[1].strip())

    elif text == "/status":
        handle_status(chat_id)

    elif text == "/stop":
        handle_stop(chat_id)

    else:
        send_message(chat_id, "Команды: /start | /register <oura_token> | /status | /stop")

    return "ok"


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
