#!/usr/bin/env python3
"""Разведка Google Health API: что реально отдаёт Fitbit Air и в каком виде.

Для каждого data type дёргает :list, печатает статус и число записей,
складывает сырые ответы в probe_output/ для разбора структуры полей.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from google_health_auth import load_env

load_env()

BASE = "https://health.googleapis.com/v4"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_output")

DATA_TYPES = [
    "sleep",
    "heart-rate-variability",
    "daily-heart-rate-variability",
    "daily-resting-heart-rate",
    "daily-oxygen-saturation",
    "oxygen-saturation",
    "daily-respiratory-rate",
    "respiratory-rate-sleep-summary",
    "daily-sleep-temperature-derivations",
    "skin-temperature-sensors",
    "heart-rate",
    "daily-heart-rate-zones",
    "steps",
    "active-zone-minutes",
    "active-minutes",
    "active-energy-burned",
    "distance",
    "sedentary-period",
    "activity-level",
    "exercise",
    "daily-vo2-max",
    "weight",
]


def get_access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_HEALTH_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def fetch(token: str, data_type: str, page_size: int = 5) -> tuple:
    url = f"{BASE}/users/me/dataTypes/{data_type}/dataPoints?pageSize={page_size}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body)
        except ValueError:
            pass
        return e.code, body


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    token = get_access_token()

    rows = []
    for dt in DATA_TYPES:
        status, payload = fetch(token, dt)
        if status == 200:
            key = next((k for k in payload if isinstance(payload.get(k), list)), None)
            records = payload.get(key) or []
            note = f"{len(records)} записей"
            if records:
                note += f", поля: {', '.join(list(records[0].keys())[:6])}"
            with open(os.path.join(OUT_DIR, f"{dt}.json"), "w") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            msg = payload
            if isinstance(payload, dict):
                msg = payload.get("error", {}).get("message", payload)
            note = f"{msg}"[:160]
        rows.append((dt, status, note))
        print(f"{status:>4}  {dt:<38} {note}")

    print(f"\nСырые ответы: {OUT_DIR}/")
    ok = sum(1 for _, s, _ in rows if s == 200)
    print(f"Доступно: {ok} из {len(rows)} типов")


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        sys.exit(f"Нет переменной {e} в .env — сначала google_health_auth.py")
