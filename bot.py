#!/usr/bin/env python3
import os
import hmac
import hashlib
import time
import jwt
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import db

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
APP_SECRET = os.getenv("APP_SECRET")
DASHBOARD_ORIGIN = os.getenv("DASHBOARD_ORIGIN", "https://demonk03.github.io")
OURA_BASE_URL = "https://api.ouraring.com/v2"

OURA_TOKEN_KEYBOARD = {
    "inline_keyboard": [[
        {"text": "Получить токен →", "url": "https://cloud.ouraring.com/personal-access-tokens"}
    ]]
}

app = Flask(__name__)


# ── CORS helper ───────────────────────────────────────────────
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = DASHBOARD_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.after_request
def after_request(response):
    return _cors(response)


# ── Telegram auth helpers ─────────────────────────────────────
def _verify_telegram_hash(data: dict) -> bool:
    """Проверяет подпись данных от Telegram Login Widget."""
    check_hash = data.get("hash")
    if not check_hash:
        return False

    fields = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))

    secret = hashlib.sha256(TG_TOKEN.encode()).digest()
    computed = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if abs(int(time.time()) - int(data.get("auth_date", 0))) > 86400:
        return False

    return hmac.compare_digest(computed, check_hash)


def _generate_jwt(user_id: str) -> str:
    """Генерирует Supabase-совместимый JWT для пользователя."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": "authenticated",
        "iss": "supabase",
        "iat": now,
        "exp": now + 7 * 24 * 3600,  # 7 дней
    }
    return jwt.encode(payload, APP_SECRET, algorithm="HS256")


def _verify_jwt(token: str) -> str | None:
    """Верифицирует JWT и возвращает user_id (sub) или None."""
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


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


@app.route("/api/logs", methods=["GET", "OPTIONS"])
def api_logs():
    if request.method == "OPTIONS":
        return "", 204
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    user_id = _verify_jwt(auth[7:])
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401
    days = int(request.args.get("days", 90))
    logs = db.get_health_logs(user_id, days=days)
    return jsonify(logs)


@app.route("/api/weekly", methods=["GET", "OPTIONS"])
def api_weekly():
    if request.method == "OPTIONS":
        return "", 204
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    user_id = _verify_jwt(auth[7:])
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401
    summary = db.get_weekly_summary(user_id)
    return jsonify(summary or {})


@app.route("/auth/telegram", methods=["POST", "OPTIONS"])
def auth_telegram():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    if not _verify_telegram_hash(dict(data)):
        return jsonify({"error": "Invalid signature"}), 401

    telegram_id = int(data["id"])
    user = db.get_user_by_telegram_id(telegram_id)

    if not user or not user.get("is_active"):
        return jsonify({
            "error": "User not registered. Use @good_morning_oura_bot to sign up."
        }), 404

    token = _generate_jwt(user["id"])
    return jsonify({
        "token": token,
        "user": {
            "name": data.get("first_name", ""),
            "telegram_id": telegram_id,
        }
    })


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
            send_message_with_keyboard(chat_id, (
                "Для регистрации отправь сообщение в формате:\n"
                "/register ваш_токен\n\n"
                "Токен можно получить на сайте Oura:"
            ), OURA_TOKEN_KEYBOARD)
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
