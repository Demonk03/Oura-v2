# Этап 0: доступ к Google Health API

Разовая настройка. Делает Дмитрий, потому что нужен браузер и его Google-аккаунт.
После шага 5 данные забирает агент — локально, из `.env`.

## Контекст

Fitbit Web API отключается 2 ноября 2026. Единственный путь — Google Health API
(`https://health.googleapis.com/v4`), OAuth 2.0 от Google вместо Fitbit PAT.

## 1. Проект в Google Cloud

1. https://console.cloud.google.com/projectcreate — имя `oura-v2-health`, location «No organization»
2. APIs & Services → Library → найти «Google Health API» → Enable

Это всё, что нужно на шаге 1. `gcloud` для проекта не требуется и не установлен —
блок ниже оставлен просто как эквивалент тех же двух действий, если CLI когда-нибудь появится.

```bash
# необязательно, то же самое что клики выше
gcloud config set project oura-v2-health
gcloud services enable health.googleapis.com
```

## 2. Consent screen

APIs & Services → OAuth consent screen (Google Auth Platform):

- App name: `Oura v2`
- User support email: свой
- Audience: **External**
- Contact email: свой

## 3. Scopes

Левая панель → **Data Access** → Add or remove scopes. Нужны три:

```
https://www.googleapis.com/auth/googlehealth.sleep.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
```

Если какого-то нет в таблице — вписать через «Manually add scopes».

## 4. Перевести в production — обязательно

Audience → **Publish app** → статус `In production`.

Причина: пока статус `Testing`, Google выдаёт refresh token с жизнью **7 дней**,
и ежедневный GitHub Actions умрёт через неделю с `invalid_grant`. В production
refresh token не истекает (кроме отзыва или 6 месяцев простоя).

Верификацию проходить не нужно: scopes restricted, поэтому на consent-экране будет
предупреждение «Google hasn't verified this app» — жать Advanced → Continue. Лимит
неверифицированного приложения — 100 пользователей, нам хватает. CASA-ассессмент
понадобился бы только после выхода за 100.

## 5. OAuth client

APIs & Services → Credentials → Create credentials → OAuth client ID:

- Type: **Web application**
- Name: `oura-v2-local`
- Authorized redirect URIs: `http://localhost:8765/callback`

Позже, для онбординга пользователей через бота, в тот же клиент добавится
`https://oura-v2.onrender.com/auth/google/callback`.

Client ID и secret — в `.env` (он в `.gitignore`):

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 6. Авторизация и разведка

```bash
python3 google_health_auth.py    # откроет браузер, допишет refresh token в .env
python3 google_health_probe.py   # обойдёт 22 data type, разложит ответы в probe_output/
```

`probe_output/` в `.gitignore` — там сырые health-данные.

## Что проверяем по результату probe

| Вопрос | Почему важно |
|---|---|
| Приходит ли `daily-heart-rate-variability` каждую ночь | HRV — основной вход в самодельный readiness |
| Есть ли `skin-temperature-sensors` / `daily-sleep-temperature-derivations` | хелп-центр Google пишет, что скин-температура только на Pixel Watch 2–5; если у Air её нет, правило `temperature_spike` выпиливается |
| Глубина истории | медианные baseline за 30 дней; если Google отдаёт мало назад, первый месяц алерты будут шумить |
| Структура `sleep.stages[]` и `summary.stagesSummary[]` | маппинг на колонки вместо Oura-полей deep/rem/light |
| Фактические имена полей в фильтрах | у `steps` это `steps.interval.start_time`, у `exercise` — `exercise.interval.civil_start_time`; единого правила нет, нужны реальные ответы |

## Известные грабли

- Скоров в API нет: ни sleep score, ни readiness, ни cardio load, ни stress.
  Это app-level метрики Google Health, наружу не отдаются. Считаем свои.
- `pageSize` для `sleep` и `exercise` — максимум 25. Без пагинации бэкфилл истории
  тихо обрежется.
- Шесть типов не поддерживают `:list`, только rollup: `floors`, `total-calories`,
  `active-minutes`, `calories-in-heart-rate-zone`, `time-in-heart-rate-zone`,
  `daily-heart-rate-zones`.
- Refresh token от OAuth Playground живёт 24 часа — для постоянной работы не годится,
  только для ручной проверки.
