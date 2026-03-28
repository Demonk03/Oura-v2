# Dashboard v2 — Design Document

Date: 2026-03-28

---

## Overview

Web-дашборд для Oura-v2 с мультипользовательской авторизацией через Telegram.
Заменяет v1 (статичный HTML + CSV) на динамический дашборд с данными из Supabase.

---

## Scope

### В этой версии
- Авторизация через Telegram Login Widget
- KPI-карточки: Readiness, Sleep, Activity, Stress
- Трендовые стрелки: день ко дню (↑ зелёная / ↓ красная / → нейтральная)
- Графики: Readiness, Sleep, Activity, Stress (как в v1, данные из Supabase)
- Блок алертов: показывать сегодняшний алерт, если есть
- Weekly recap: текст из `weekly_summaries` за текущую неделю

### Backlog (не в этой версии)
- Email + пароль авторизация
- Инсайт дня (GPT-генерация)
- Фильтр масштаба графиков
- Аннотации на графиках

---

## Architecture

```
[GitHub Pages]          [Render.com]           [Supabase]
  dashboard.html  --->  POST /auth/telegram  -->  users (lookup by telegram_id)
                  <---  JWT (signed)         <--

  dashboard.html  --->  Supabase JS SDK (with JWT as Bearer)
                  <---  health_logs, weekly_summaries, alerts (RLS enforced)
```

**Hosting:** GitHub Pages (статика, бесплатно)
**Auth flow:** Telegram Widget → Render verifies → returns Supabase-compatible JWT
**Data access:** Frontend → Supabase JS SDK напрямую, JWT в Authorization header
**Security:** Supabase RLS на всех таблицах, `auth.uid()` = UUID пользователя из `users`

---

## Auth Flow (детально)

1. Пользователь открывает дашборд, видит кнопку "Войти через Telegram"
2. Telegram Login Widget открывает попап, пользователь авторизуется в Telegram-приложении
3. Виджет вызывает callback с объектом `{ id, first_name, hash, auth_date, ... }`
4. Frontend делает `POST /auth/telegram` на Render с этим объектом
5. Render:
   - Верифицирует `hash` через HMAC-SHA256 с bot token
   - Проверяет `auth_date` — не старше 24 часов
   - Находит пользователя по `telegram_id` в таблице `users` (service role)
   - Если пользователь не найден → возвращает 404 с сообщением "Сначала зарегистрируйтесь через бота @good_morning_oura_bot"
   - Генерирует JWT: `{ sub: user.id, role: "authenticated", iss: "supabase" }`, подписывает секретом из Supabase JWT Secret
   - Возвращает `{ token, user: { name, telegram_id } }`
6. Frontend сохраняет JWT в `localStorage`
7. При следующих открытиях — проверяет наличие и срок JWT в localStorage, если валиден — сразу авторизован

**Срок JWT:** 7 дней (баланс между удобством и безопасностью)

---

## Supabase Changes

### RLS Policies (добавить на все таблицы)

```sql
-- health_logs
CREATE POLICY "users_own_data" ON health_logs
  FOR SELECT USING (user_id = auth.uid());

-- weekly_summaries
CREATE POLICY "users_own_summaries" ON weekly_summaries
  FOR SELECT USING (user_id = auth.uid());

-- alerts (новая таблица, см. ниже)
CREATE POLICY "users_own_alerts" ON alerts
  FOR SELECT USING (user_id = auth.uid());
```

### Новая таблица: alerts

Текущий `alert_checker.py` генерирует и отправляет алерт в Telegram, но не сохраняет в БД.
Нужно добавить хранение, чтобы дашборд мог показывать сегодняшний алерт.

```sql
CREATE TABLE alerts (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id),
  date       DATE NOT NULL,
  text       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, date)
);
```

`alert_checker.py` нужно обновить: после отправки в Telegram — писать запись в `alerts`.

---

## Render.com Changes

Добавить в `bot.py` один эндпоинт:

```
POST /auth/telegram
Body: { id, first_name, last_name, username, photo_url, auth_date, hash }
Response 200: { token: "<jwt>", user: { name, telegram_id } }
Response 401: { error: "Invalid signature" }
Response 404: { error: "User not registered. Use @good_morning_oura_bot to sign up." }
```

Зависимости: добавить `PyJWT` в `requirements.txt`.

Новые env vars на Render:
- `SUPABASE_JWT_SECRET` — JWT Secret из Supabase Settings → API

---

## Frontend Structure

```
Oura-v2/
├── dashboard/
│   ├── index.html        — главная страница дашборда
│   ├── login.html        — страница логина (Telegram Widget)
│   ├── dashboard.css     — стили (основа из v1 index.css)
│   └── dashboard.js      — логика: auth, data fetching, charts, render
```

### Страницы

**login.html**
- Telegram Login Widget
- Сообщение "Нет аккаунта? Напишите @good_morning_oura_bot"

**index.html** (дашборд)
- Header: имя пользователя, кнопка "Выйти", дата сегодня
- Блок алерта (скрыт если нет алерта): жёлтый/оранжевый баннер с текстом алерта
- KPI секция: 4 карточки с кружком-счётчиком + стрелка + дельта
- Weekly recap: карточка с текстом из weekly_summaries
- Графики: 4 графика (Chart.js, как в v1)
- Фильтр диапазона: 7 дней / 30 дней / весь период

### Стрелки (день ко дню)

```
Readiness  [82]  ↑ +5   (зелёная)
Sleep      [71]  ↓ -8   (красная)
Activity   [75]  →  0   (серая)
```

Порог нейтральной зоны: ±2 балла → серая стрелка.

---

## Data Fetching

При загрузке дашборда:

1. **Последние 31 день** из `health_logs` — для графиков и дельт
2. **Сегодняшний алерт** из `alerts` (WHERE date = today)
3. **Последний weekly recap** из `weekly_summaries` (ORDER BY week_start DESC LIMIT 1)

Все запросы через Supabase JS SDK с JWT в header.

---

## GitHub Pages Deployment

```
repository: Demonk03/Oura-v2
branch: main
folder: /dashboard
URL: https://demonk03.github.io/Oura-v2/dashboard/
```

Настройка: GitHub Settings → Pages → Source: Deploy from branch, folder `/dashboard`.

---

## Backlog

| Фича | Описание |
|---|---|
| Email auth | Supabase built-in email+password, маппинг на `users` по email полю |
| Инсайт дня | GitHub Action генерирует GPT-инсайт, хранит в новом поле/таблице |
| Аннотации на графиках | Метки на точках с тегами (алкоголь, болезнь) |
| Фильтр масштаба | Готовая кнопка в v1 — подключить логику |
