#!/usr/bin/env python3
"""Сбор данных Fitbit Air через Google Health API в таблицу fitbit_logs.

Запускается по расписанию. Всегда перезабирает последние WINDOW_DAYS дней:
Google досчитывает температуру, HRV и дыхание задним числом, поэтому запись
за сегодня к утру неполная и её надо перезаписывать.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date as date_cls, datetime, timedelta, timezone

import db
from google_health_auth import load_env

load_env()

BASE = "https://health.googleapis.com/v4"
WINDOW_DAYS = 7

# Активность берём только с браслета: иначе в ряд подмешиваются шаги с телефона.
WEARABLES = "users/me/dataSourceFamilies/google-wearables"

# Дневные типы: одна запись на дату, поле date приходит в ответе.
DAILY_TYPES = {
    "daily-heart-rate-variability": "dailyHeartRateVariability",
    "daily-resting-heart-rate": "dailyRestingHeartRate",
    "daily-respiratory-rate": "dailyRespiratoryRate",
    "daily-oxygen-saturation": "dailyOxygenSaturation",
    "daily-sleep-temperature-derivations": "dailySleepTemperatureDerivations",
    "daily-vo2-max": "dailyVo2Max",
}

# Поминутные типы: только через dailyRollUp.
ROLLUP_TYPES = [
    "steps", "distance", "total-calories", "active-energy-burned",
    "sedentary-period", "active-zone-minutes", "heart-rate",
]


def get_access_token(refresh_token: str) -> str:
    data = urllib.parse.urlencode({
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def _api(token: str, path: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers,
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_list(token: str, data_type: str, page_size: int = 100) -> list:
    """Фильтры :list по датам в документации не описаны и отличаются от типа
    к типу, поэтому берём последнюю страницу и отсекаем по дате на своей стороне."""
    path = f"/users/me/dataTypes/{data_type}/dataPoints?pageSize={page_size}"
    return _api(token, path).get("dataPoints") or []


def fetch_daily_rollup(token: str, data_type: str, start: date_cls, end: date_cls) -> list:
    body = {
        "range": {
            "start": {"date": {"year": start.year, "month": start.month, "day": start.day}},
            "end": {"date": {"year": end.year, "month": end.month, "day": end.day}},
        },
        "windowSizeDays": 1,
        "dataSourceFamily": WEARABLES,
    }
    path = f"/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp"
    return _api(token, path, body).get("rollupDataPoints") or []


def _date(d: dict) -> str:
    return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"


def _civil_date(iso_time: str, utc_offset: str) -> str:
    """Дата в локальном времени пользователя. Смещение приходит как '10800s'."""
    t = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    seconds = int((utc_offset or "0s").rstrip("s"))
    return (t.astimezone(timezone.utc) + timedelta(seconds=seconds)).date().isoformat()


def _int(v):
    return int(float(v)) if v is not None else None


def _num(v):
    """Google присылает NaN там, где базовой линии ещё не хватает истории —
    например в baselineTemperatureCelsius в первые недели носки."""
    if v is None:
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def collect_daily(token: str, days: set) -> dict:
    out = defaultdict(dict)
    for data_type, field in DAILY_TYPES.items():
        for pt in fetch_list(token, data_type):
            v = pt.get(field) or {}
            if not v.get("date"):
                continue
            d = _date(v["date"])
            if d not in days:
                continue
            if data_type == "daily-heart-rate-variability":
                out[d].update({
                    "average_hrv": _num(v.get("averageHeartRateVariabilityMilliseconds")),
                    "deep_sleep_rmssd": _num(v.get("deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds")),
                    "hrv_entropy": _num(v.get("entropy")),
                    "non_rem_hr": _int(v.get("nonRemHeartRateBeatsPerMinute")),
                })
            elif data_type == "daily-resting-heart-rate":
                meta = v.get("dailyRestingHeartRateMetadata") or {}
                out[d].update({
                    "resting_hr": _int(v.get("beatsPerMinute")),
                    "resting_hr_method": meta.get("calculationMethod"),
                })
            elif data_type == "daily-respiratory-rate":
                out[d]["average_breath"] = _num(v.get("breathsPerMinute"))
            elif data_type == "daily-oxygen-saturation":
                out[d].update({
                    "spo2_average": _num(v.get("averagePercentage")),
                    "spo2_min": _num(v.get("lowerBoundPercentage")),
                    "spo2_max": _num(v.get("upperBoundPercentage")),
                })
            elif data_type == "daily-sleep-temperature-derivations":
                nightly = _num(v.get("nightlyTemperatureCelsius"))
                baseline = _num(v.get("baselineTemperatureCelsius"))
                out[d].update({
                    "nightly_temp": nightly,
                    "baseline_temp": baseline,
                    "temp_rel_stddev_30d": _num(v.get("relativeNightlyStddev30dCelsius")),
                    "temperature_deviation": (nightly - baseline)
                    if nightly is not None and baseline is not None else None,
                })
            elif data_type == "daily-vo2-max":
                out[d].update({
                    "vo2_max": _num(v.get("vo2Max")),
                    "cardio_fitness_level": v.get("cardioFitnessLevel"),
                })
    return out


def collect_rollups(token: str, start: date_cls, end: date_cls) -> dict:
    out = defaultdict(dict)
    for data_type in ROLLUP_TYPES:
        for pt in fetch_daily_rollup(token, data_type, start, end):
            cs = (pt.get("civilStartTime") or {}).get("date")
            if not cs:
                continue
            d = _date(cs)
            if data_type == "steps":
                out[d]["steps"] = _int((pt.get("steps") or {}).get("countSum"))
            elif data_type == "distance":
                mm = _int((pt.get("distance") or {}).get("millimetersSum"))
                out[d]["distance_m"] = mm // 1000 if mm is not None else None
            elif data_type == "total-calories":
                out[d]["total_calories"] = _int((pt.get("totalCalories") or {}).get("kcalSum"))
            elif data_type == "active-energy-burned":
                out[d]["active_calories"] = _int((pt.get("activeEnergyBurned") or {}).get("kcalSum"))
            elif data_type == "sedentary-period":
                dur = (pt.get("sedentaryPeriod") or {}).get("durationSum")
                out[d]["sedentary_time"] = _int(dur.rstrip("s")) if dur else None
            elif data_type == "active-zone-minutes":
                azm = pt.get("activeZoneMinutes") or {}
                out[d].update({
                    "azm_fat_burn": _int(azm.get("sumInFatBurnHeartZone")),
                    "azm_cardio": _int(azm.get("sumInCardioHeartZone")),
                    "azm_peak": _int(azm.get("sumInPeakHeartZone")),
                })
            elif data_type == "heart-rate":
                hr = pt.get("heartRate") or {}
                out[d].update({
                    "hr_avg": _num(hr.get("beatsPerMinuteAvg")),
                    "hr_min": _int(hr.get("beatsPerMinuteMin")),
                    "hr_max": _int(hr.get("beatsPerMinuteMax")),
                })
    return out


def collect_sleep(token: str, days: set) -> dict:
    """За сутки может быть несколько записей: основная ночь плюс дневной сон.
    Самая длинная идёт в основные поля, остальные считаются как naps.
    Запись относится к дате пробуждения."""
    by_day = defaultdict(list)
    for pt in fetch_list(token, "sleep", page_size=25):
        s = pt.get("sleep") or {}
        iv = s.get("interval") or {}
        if not iv.get("endTime"):
            continue
        d = _civil_date(iv["endTime"], iv.get("endUtcOffset"))
        if d in days:
            by_day[d].append(s)

    out = {}
    for d, sessions in by_day.items():
        def duration(s):
            iv = s["interval"]
            start = datetime.fromisoformat(iv["startTime"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(iv["endTime"].replace("Z", "+00:00"))
            return (end - start).total_seconds()

        sessions.sort(key=duration, reverse=True)
        main, naps = sessions[0], sessions[1:]
        iv = main["interval"]
        stages = defaultdict(int)
        for st in main.get("stages") or []:
            start = datetime.fromisoformat(st["startTime"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(st["endTime"].replace("Z", "+00:00"))
            stages[st["type"]] += int((end - start).total_seconds())

        in_bed = int(duration(main))
        asleep = stages["LIGHT"] + stages["DEEP"] + stages["REM"]
        out[d] = {
            "sleep_start": iv["startTime"],
            "sleep_end": iv["endTime"],
            "time_in_bed": in_bed,
            "total_sleep_duration": asleep,
            "awake_time": stages["AWAKE"],
            "light_sleep_duration": stages["LIGHT"],
            "deep_sleep_duration": stages["DEEP"],
            "rem_sleep_duration": stages["REM"],
            "nap_count": len(naps),
            "nap_duration": int(sum(duration(n) for n in naps)),
        }
    return out


def collect_workouts(token: str, days: set) -> dict:
    by_day = defaultdict(list)
    for pt in fetch_list(token, "exercise", page_size=25):
        e = pt.get("exercise") or {}
        iv = e.get("interval") or {}
        if not iv.get("startTime"):
            continue
        d = _civil_date(iv["startTime"], iv.get("startUtcOffset"))
        if d in days:
            by_day[d].append(e)

    out = {}
    for d, items in by_day.items():
        total_seconds = 0
        for e in items:
            iv = e["interval"]
            start = datetime.fromisoformat(iv["startTime"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(iv["endTime"].replace("Z", "+00:00"))
            total_seconds += int((end - start).total_seconds())
        summaries = [e.get("metricsSummary") or {} for e in items]
        out[d] = {
            "workout_count": len(items),
            "workout_types": ", ".join(sorted({e.get("exerciseType", "UNKNOWN") for e in items})),
            "workout_calories": sum(_int(s.get("caloriesKcal")) or 0 for s in summaries),
            "workout_distance": sum(_int(s.get("distanceMillimeters")) or 0 for s in summaries) // 1000,
            "workout_duration": total_seconds,
        }
    return out


def run_for_user(user: dict, window_days: int) -> int:
    token = get_access_token(user["google_refresh_token"])
    end = date_cls.today() + timedelta(days=1)       # end в rollup эксклюзивный
    start = date_cls.today() - timedelta(days=window_days - 1)
    days = {(start + timedelta(days=i)).isoformat() for i in range((end - start).days)}

    merged = defaultdict(dict)
    for part in (collect_daily(token, days), collect_rollups(token, start, end),
                 collect_sleep(token, days), collect_workouts(token, days)):
        for d, fields in part.items():
            merged[d].update(fields)

    written = 0
    for d in sorted(merged):
        fields = {k: v for k, v in merged[d].items() if v is not None}
        if not fields:
            continue
        db.upsert_fitbit_log(user["id"], d, fields)
        written += 1
        print(f"  {d}: {len(fields)} полей")
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=WINDOW_DAYS,
                        help=f"сколько последних дней перезабрать (по умолчанию {WINDOW_DAYS})")
    args = parser.parse_args()

    users = db.get_fitbit_users()
    if not users:
        print("Нет пользователей с подключённым Google Health")
        return

    for user in users:
        print(f"Пользователь {user['id']}:")
        try:
            written = run_for_user(user, args.days)
            print(f"  записано дней: {written}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            print(f"  ошибка {e.code}: {body}")
            if e.code in (400, 401) and "invalid_grant" in body:
                print("  refresh token отозван — нужна повторная авторизация")


if __name__ == "__main__":
    main()
