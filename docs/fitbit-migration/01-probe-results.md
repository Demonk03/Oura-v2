# Этап 0: результаты разведки

Прогон `google_health_probe.py` от 27.10.2026. Устройство — Fitbit Air,
`platform: FITBIT`, `formFactor: FITNESS_BAND`.

## Доступность

21 тип из 22 отвечает 200. Единственная ошибка — `skin-temperature-sensors`:
`Invalid data type ID`. Это ошибка в нашем списке, а не отсутствие данных —
температура приходит через `daily-sleep-temperature-derivations`.

**Правило `temperature_spike` выживает.**

## Глубина истории — главное ограничение

| Тип | Записи | Период |
|---|---|---|
| `daily-resting-heart-rate` | 19 | 08.08 – 27.10 |
| `daily-heart-rate-variability` | 18 | 08.08 – 27.10 |
| `sleep` | 4 | 24.10 – 26.10 |
| `daily-sleep-temperature-derivations` | 3 | 25.10 – 27.10 |
| `daily-respiratory-rate` | 3 | 25.10 – 27.10 |
| `daily-oxygen-saturation` | 1 | 25.10 |
| `steps`, `distance` (dailyRollUp) | 8 дней | 20.10 – 27.10 |

Браслет носится примерно с 24.10. HRV и пульс покоя формально тянутся с августа,
но 19 записей на 80 дней — это не ежедневный ряд; откуда они, вопрос открытый.
Шаги и расстояние есть до начала ношения — вероятно, с телефона.

**Следствие:** медианные baseline за 30 дней заработают не раньше конца ноября.
Строить и калибровать формулу скора сейчас не на чем. Собирать данные надо начинать
немедленно, скоринг и алерты — после накопления.

## Скоров нет, подтверждено

Ни sleep score, ни readiness, ни cardio load, ни stress. В `sleep` есть стадии
и длительность, но не оценка.

## Зато Google отдаёт готовые baseline

Неожиданная находка, упрощающая этап 1:

- `daily-sleep-temperature-derivations` → `nightlyTemperatureCelsius`,
  `baselineTemperatureCelsius`, `relativeNightlyStddev30dCelsius`.
  Отклонение считать не надо, оно фактически уже посчитано
- `dailyRollUp` по `daily-heart-rate-variability` → `heartRateVariabilityPersonalRange`
  (min/max персонального диапазона)
- `dailyRollUp` по `daily-resting-heart-rate` → `restingHeartRatePersonalRange`

То есть часть работы, которую мы собирались делать сами на медианах, уже сделана
на стороне Google и на большей выборке.

## Что реально приходит

**`daily-heart-rate-variability`** — богаче, чем у Oura:
`averageHeartRateVariabilityMilliseconds`, `deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds`,
`nonRemHeartRateBeatsPerMinute`, `entropy`.

**`daily-resting-heart-rate`** — `beatsPerMinute` + `calculationMethod` (`WITH_SLEEP`).

**`respiratory-rate-sleep-summary`** — частота дыхания отдельно по стадиям сна,
с `standardDeviation` и `signalToNoise`.

**`sleep`** — `type: STAGES`, массив `stages[]` с `AWAKE/LIGHT/DEEP/REM`.
За 24.10 две записи: ночь и, судя по всему, дневной сон. Один день ≠ одна запись,
агрегировать придётся самим.

**`exercise`** — автодетект работает: теннис 26.10, `caloriesKcal`, `steps`,
`averageHeartRateBeatsPerMinute`, `activeZoneMinutes`, длительности по зонам пульса.

## Гранулярность: list vs dailyRollUp

`steps`, `distance`, `active-minutes`, `activity-level`, `heart-rate` приходят
**поминутно**. За сутки это сотни точек, `:list` для них бесполезен.

Использовать `:dailyRollUp`. Форма тела запроса (в документации её нет, добыта
из discovery-документа `https://health.googleapis.com/$discovery/rest?version=v4`):

```json
{
  "range": {
    "start": {"date": {"year": 2026, "month": 10, "day": 20}},
    "end":   {"date": {"year": 2026, "month": 10, "day": 28}}
  },
  "windowSizeDays": 1
}
```

Поля именно `start` / `end`, а не `startTime` / `endTime` — последние дают 400.
Диапазон полуоткрытый: `end` не включается. По умолчанию отдаётся до 90 окон.

Проверенные ответы: `steps.countSum`, `distance.millimetersSum`,
`totalCalories.kcalSum`, `sedentaryPeriod.durationSum`,
`activeZoneMinutes.sumIn{FatBurn,Cardio,Peak}HeartZone`,
`heartRate.beatsPerMinute{Avg,Min,Max}`.

## Открытые вопросы

- **Смешение источников.** Шаги есть за дни до начала ношения браслета — значит
  в ряд попадает телефон. У rollup-методов есть параметр `dataSourceFamily`;
  надо проверить, отделяет ли он Fitbit от телефона, иначе активность будет врать
- Откуда HRV и пульс покоя с августа, если браслет с октября
- Нужна ли дедупликация `sleep`, когда за сутки несколько записей
