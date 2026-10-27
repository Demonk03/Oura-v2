# План: переход с Oura Ring на Fitbit Air

Контекст и находки по API — `docs/fitbit-migration/00-google-health-setup.md`.

## Решения

- Живём в этом же репозитории, рядом с Oura-данными. Новая таблица `fitbit_logs`,
  `health_logs` с историей Oura с февраля 2026 не трогаем
- Источник — Google Health API напрямую (не Apple Health, не агрегатор).
  Apple Health отпадает: Google Health не пишет в HealthKit HRV и скин-температуру
- Композитных скоров в API нет — считаем свои из сырых метрик
- Oura-ветка остаётся работоспособной, пока оба устройства живы

## Этап 0 — доступ и разведка

- [x] Создать GCP-проект, включить `health.googleapis.com`, настроить consent screen
- [x] Опубликовать политику конфиденциальности — без неё Google не отдаёт production
- [x] Перевести OAuth-приложение в статус `In production` (иначе refresh token живёт 7 дней)
- [ ] Создать OAuth client, положить `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET` в `.env`
- [x] Прогнать `google_health_auth.py`, получить refresh token
- [x] Прогнать `google_health_probe.py`, разобрать `probe_output/`
- [x] Зафиксировать результат разведки — `docs/fitbit-migration/01-probe-results.md`
- [ ] Через 8 дней после авторизации проверить, что refresh token жив.
      Если `invalid_grant` — значит production-статус не спас и нужен план Б
      (верификация с CASA либо еженедельная переавторизация)

## Этап 1 — формула скоров

**Сдвинут на конец ноября.** Разведка показала, что браслет носится с 24.10:
ряд HRV, температуры и дыхания — три дня. Калибровать формулу не на чем,
сначала надо накопить данные, поэтому порядок работ теперь 2 → 3 → 1 → 5.

- [x] Проверить, остаётся ли `temperature_spike` — да, через
      `daily-sleep-temperature-derivations`
- [ ] Выбрать входы readiness (HRV, RHR, длительность и стадии сна, дыхание)
- [ ] Использовать готовые baseline Google (`baselineTemperatureCelsius`,
      `heartRateVariabilityPersonalRange`, `restingHeartRatePersonalRange`)
      вместо собственных медиан там, где они есть
- [ ] Описать формулу, зафиксировать в документе
- [ ] Решить судьбу правил без источника: `readiness_low`, `sleep_crash`,
      `sleep_trend_down`, `stress_balance_worsening`

## Этап 2 — схема данных

- [x] Таблица `fitbit_logs`: UNIQUE(user_id, date), сырые метрики + вычисленные скоры
- [x] В `users` добавить `google_refresh_token`, `google_health_user_id`, `source`
- [x] Маркер неполной записи не нужен: каждый прогон перезабирает последние 7 дней

## Этап 3 — сбор данных

Приоритет номер один: чем раньше запустится сбор, тем раньше накопится baseline.

- [x] `fitbit_update.py`: обмен refresh token на access token, обход типов, upsert
- [x] Дневные агрегаты через `:dailyRollUp` для `steps`, `distance`, `heart-rate`,
      `total-calories`, `sedentary-period`, `active-zone-minutes` — они поминутные,
      `:list` для них не годится
- [x] Проверить `dataSourceFamily` — да, отделяет. Активность собирать только
      с `users/me/dataSourceFamilies/google-wearables`
- [x] Агрегация `sleep`, когда за сутки несколько записей: самая длинная сессия
      идёт в основные поля, остальные считаются как naps
- [x] GitHub Actions workflow + секреты `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
      Refresh token в секретах не нужен, он читается из `users`
- [x] Бэкфилл: собраны все доступные дни (24–27.10), больше в API нет
- [ ] Пагинация для `sleep` и `exercise` — сейчас берётся одна страница на 25
      записей. Хватает для окна в 7 дней, понадобится при длинной истории
- [ ] Расчёт скоров при записи дня — после этапа 1

## Этап 4 — онбординг через бота

- [ ] `/auth/google/start` и `/auth/google/callback` в `bot.py`
- [ ] Добавить `https://oura-v2.onrender.com/auth/google/callback` в OAuth client
- [ ] Заменить `/register <token>` на кнопку «Подключить Fitbit»
- [ ] Обработка отозванного токена: `invalid_grant` → уведомление в Telegram

## Этап 5 — алерты, дайджест, дашборд

- [ ] `alert_checker.py` на новые поля и новые скоры
- [ ] `gpt_table_analyzer.py`: новый набор колонок для weekly
- [ ] `dashboard.js`: графики по Fitbit-метрикам, переключение источника
- [ ] Проверить, что Oura-ветка не сломалась

## Tennis Coach зависит от Oura — починить отдельно

База общая. У `match_prep` внешний ключ на `health_logs` и колонки
`oura_readiness`, `oura_sleep_score`, `oura_hrv`, `oura_is_stale`. Когда кольцо
перестанет носиться, теннисный тренер молча встанет на устаревших данных.

- [ ] Решить, переводить ли `match_prep` на `fitbit_logs` или на общий слой
- [ ] Задача живёт в проекте `tennis-coach`, не здесь

## Отложено

- [ ] Webhook-подписки Google Health вместо ежедневного polling
- [ ] Регистрация `Oura-v2` в реестре скилла `sync-ticktick` (нет TickTick project ID)

## Риски

- Google второй год перетряхивает API: Google Fit → Fitbit Web API → Google Health API,
  `v4beta` открыт 01.10.2026. Ещё одна миграция в пределах года вероятна
- Если глубина истории мала, медианные baseline заработают только через месяц носки,
  и первый месяц алерты будут шумить
- Неверифицированное приложение: лимит 100 пользователей, consent-экран с предупреждением
