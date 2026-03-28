#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import db

load_dotenv()

BASE_URL = "https://api.ouraring.com/v2"
START_DATE = "2026-02-01"

READINESS_MAP = {
    "activity_balance": "activity_balance",
    "body_temperature": "body_temp",
    "hrv_balance": "hrv_balance",
    "previous_day_activity": "prev_day",
    "previous_night": "prev_night",
    "recovery_index": "recovery",
    "resting_heart_rate": "resting_hr",
    "sleep_balance": "sleep_balance",
}

SLEEP_MAP = {
    "deep_sleep": "deep",
    "efficiency": "efficiency",
    "latency": "latency",
    "rem_sleep": "rem",
    "restfulness": "restfulness",
    "timing": "timing",
    "total_sleep": "total",
}

ACTIVITY_MAP = {
    "meet_daily_targets": "meet_targets",
    "move_every_hour": "move_hour",
    "recovery_time": "recovery",
    "stay_active": "stay_active",
    "training_frequency": "train_freq",
    "training_volume": "train_vol",
}

RESILIENCE_MAP = {
    "sleep_recovery": "sleep",
    "daytime_recovery": "daytime",
    "stress": "stress",
}

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


def _int(v):
    return int(v) if v is not None else None


def build_day_fields(date: str, oura_pat: str) -> dict:
    """Собирает все поля для одного дня из всех эндпоинтов."""
    fields = {}

    # daily_readiness
    data = fetch_endpoint(oura_pat, ENDPOINTS["daily_readiness"], date, date)
    if data:
        r = data[0]
        fields.update({
            "readiness_score": _int(r.get("score")),
            "temperature_deviation": r.get("temperature_deviation"),
            "temperature_trend_deviation": r.get("temperature_trend_deviation"),
        })
        for k, v in (r.get("contributors") or {}).items():
            col = READINESS_MAP.get(k)
            if col:
                fields[f"readiness_{col}_score"] = _int(v)

    # daily_sleep
    data = fetch_endpoint(oura_pat, ENDPOINTS["daily_sleep"], date, date)
    if data:
        r = data[0]
        fields["sleep_score"] = _int(r.get("score"))
        for k, v in (r.get("contributors") or {}).items():
            col = SLEEP_MAP.get(k)
            if col:
                fields[f"sleep_{col}_score"] = _int(v)

    # daily_activity
    data = fetch_endpoint(oura_pat, ENDPOINTS["daily_activity"], date, date)
    if data:
        r = data[0]
        fields.update({
            "activity_score": _int(r.get("score")),
            "steps": _int(r.get("steps")),
            "active_calories": _int(r.get("active_calories")),
            "total_calories": _int(r.get("total_calories")),
            "walking_distance": _int(r.get("equivalent_walking_distance")),
            "high_activity_time": _int(r.get("high_activity_time")),
            "sedentary_time": _int(r.get("sedentary_time")),
        })
        for k, v in (r.get("contributors") or {}).items():
            col = ACTIVITY_MAP.get(k)
            if col:
                fields[f"activity_{col}_score"] = _int(v)

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
            col = RESILIENCE_MAP.get(k)
            if col:
                fields[f"resilience_{col}_score"] = _int(v)

    # sleep (детальные данные)
    data = fetch_endpoint(oura_pat, ENDPOINTS["sleep"], date, date)
    long_sleeps = [s for s in data if s.get("type") == "long_sleep"]
    short_sleeps = [s for s in data if s.get("type") == "short_sleep"]
    if long_sleeps:
        s = long_sleeps[0]
        fields.update({
            "average_heart_rate": _int(s.get("average_heart_rate")),
            "lowest_heart_rate": _int(s.get("lowest_heart_rate")),
            "average_hrv": _int(s.get("average_hrv")),
            "average_breath": s.get("average_breath"),
            "efficiency": _int(s.get("efficiency")),
            "latency": _int(s.get("latency")),
            "time_in_bed": _int(s.get("time_in_bed")),
            "total_sleep_duration": _int(s.get("total_sleep_duration")),
            "awake_time": _int(s.get("awake_time")),
            "light_sleep_duration": _int(s.get("light_sleep_duration")),
            "deep_sleep_duration": _int(s.get("deep_sleep_duration")),
            "rem_sleep_duration": _int(s.get("rem_sleep_duration")),
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
