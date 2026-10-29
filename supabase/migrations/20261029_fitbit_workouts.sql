-- Одна строка = один dataPoint из exercise Google Health API.
-- Дневной агрегат в fitbit_logs (workout_count/types/duration/calories/distance)
-- остаётся как есть: там сумма по дню, здесь отдельные сессии.
--
-- Идемпотентность держится на source_point_name — имени точки из API.
-- Поэтому ежедневный перезабор последних 7 дней безопасно переписывает
-- те же записи, а не плодит дубли.
--
-- Перекрывающиеся записи (ручная отметка + автодетект одного занятия)
-- намеренно не схлопываются: это разные dataPoint'ы, отличать их
-- на чтении по recording_method.

create table if not exists fitbit_workouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  source_point_name text not null unique,

  start_time timestamptz not null,
  end_time timestamptz not null,
  utc_offset_seconds integer,
  -- Локальная дата начала: по ней сопоставляются матчи и тренировки.
  -- Вечерняя сессия в UTC может уехать на следующие сутки.
  local_date date generated always as (
    ((start_time at time zone 'UTC') + make_interval(secs => utc_offset_seconds))::date
  ) stored,
  -- activeDuration из API: это не end_time - start_time, пауза не считается.
  active_duration_seconds integer,

  exercise_type text not null,
  display_name text,
  recording_method text,
  device_form_factor text,
  device_name text,

  avg_hr integer,
  active_zone_minutes integer,
  hr_light_seconds integer,
  hr_moderate_seconds integer,
  hr_vigorous_seconds integer,
  hr_peak_seconds integer,

  calories_kcal integer,
  steps integer,
  distance_m integer,
  avg_pace_sec_per_m double precision,

  synced_at timestamptz not null default now()
);

create index if not exists fitbit_workouts_user_start_idx
  on fitbit_workouts (user_id, start_time desc);

create index if not exists fitbit_workouts_user_type_date_idx
  on fitbit_workouts (user_id, exercise_type, local_date);

-- Как у остальных таблиц проекта: RLS включён, policies нет.
-- Доступ только service-role ключом со стороны сервера.
alter table fitbit_workouts enable row level security;
