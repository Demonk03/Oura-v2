import os
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
